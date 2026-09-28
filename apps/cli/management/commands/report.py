import csv
from collections import defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.billing.models import Bill
from apps.customers.models import Customer

# Khordad + Tir 1405. end_date_jalali is stored as 'YYYY/MM/DD' (zero-padded),
# so plain string comparison is equivalent to date comparison.
JALALI_START = '1405/03/01'          # inclusive: first day of Khordad
JALALI_END_EXCLUSIVE = '1405/05/01'  # exclusive: first day of Mordad

NO_VALUE_LABEL = 'No value / NULL'
DEFAULT_OUTPUT_DIR = 'reports/khordad_tir_1405'

# utf-8-sig adds a BOM so Excel opens Persian text correctly.
CSV_ENCODING = 'utf-8-sig'


class Command(BaseCommand):
    help = (
        'Prints customers with a bill ending in Khordad/Tir 1405 (by end_date_jalali), '
        'broken down by several attributes, and exports each request to its own CSV file.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--show-customers',
            action='store_true',
            help=(
                'Also list the bill_identity values inside every breakdown group '
                '(console output, and an extra *_customers.csv file per request).'
            ),
        )
        parser.add_argument(
            '--output-dir',
            default=DEFAULT_OUTPUT_DIR,
            help=f'Directory the CSV files are written to (default: {DEFAULT_OUTPUT_DIR}).',
        )

    def handle(self, *args, **options):
        show_customers = options['show_customers']
        self.output_dir = Path(options['output_dir'])
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise CommandError(f'Cannot create output directory {self.output_dir}: {exc}')

        bills_qs = Bill.objects.filter(
            end_date_jalali__gte=JALALI_START,
            end_date_jalali__lt=JALALI_END_EXCLUSIVE,
        ).values(
            'customer_id',
            'bill_type_name',
            'change_reason_id',
            'change_reason_name',
        )
        bill_rows = list(bills_qs)

        if not bill_rows:
            self.stdout.write(self.style.WARNING('No bills found for Khordad/Tir 1405.'))
            return

        customer_ids = sorted({row['customer_id'] for row in bill_rows})

        customers_qs = Customer.objects.filter(bill_identity__in=customer_ids)
        customers = {c.bill_identity: c for c in customers_qs}

        self._print_customer_list(customer_ids)

        self._print_bill_level_breakdown(
            'Request 2: Bill type (definite / interim / ...)',
            'request2_bill_type',
            bill_rows,
            lambda row: row['bill_type_name'] or NO_VALUE_LABEL,
            show_customers,
            sql=self._sql_bill_level(f"COALESCE(NULLIF(b.bill_type_name, ''), '{NO_VALUE_LABEL}')"),
        )

        self._print_customer_level_breakdown(
            'Request 3: Faham / Non-Faham',
            'request3_faham',
            customers,
            lambda c: c.subscriber_type or NO_VALUE_LABEL,
            show_customers,
            sql=self._sql_customer_level(f"COALESCE(NULLIF(c.subscriber_type, ''), '{NO_VALUE_LABEL}')"),
        )

        self._print_customer_level_breakdown(
            'Request 4: Tariff type (usage group)',
            'request4_tariff_type',
            customers,
            lambda c: c.usage_group_name or NO_VALUE_LABEL,
            show_customers,
            sql=self._sql_customer_level(f"COALESCE(NULLIF(c.usage_group_name, ''), '{NO_VALUE_LABEL}')"),
        )

        self._print_customer_level_breakdown(
            'Request 5: Region office (Omor)',
            'request5_region_office',
            customers,
            lambda c: c.omor_name or NO_VALUE_LABEL,
            show_customers,
            sql=self._sql_customer_level(f"COALESCE(NULLIF(c.omor_name, ''), '{NO_VALUE_LABEL}')"),
        )

        self._print_bill_level_breakdown(
            'Request 6: Agent observe code (Shahed code)',
            'request6_observe_code',
            bill_rows,
            lambda row: (
                f'{row["change_reason_id"]} - {row["change_reason_name"]}'
                if row['change_reason_id'] is not None
                else NO_VALUE_LABEL
            ),
            show_customers,
            sql=self._sql_bill_level(
                "CASE WHEN b.change_reason_id IS NOT NULL "
                "THEN CONCAT(b.change_reason_id, ' - ', b.change_reason_name) "
                f"ELSE '{NO_VALUE_LABEL}' END"
            ),
        )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'CSV files written to: {self.output_dir.resolve()}'))

    # ------------------------------------------------------------------ #
    # Sample raw PostgreSQL (printed above each request's result)
    # Column names are assumed to match the model field names.
    # ------------------------------------------------------------------ #
    @staticmethod
    def _bill_table():
        return Bill._meta.db_table

    @staticmethod
    def _customer_table():
        return Customer._meta.db_table

    def _base_where(self, alias='b'):
        return (
            f"{alias}.end_date_jalali >= '{JALALI_START}' "
            f"AND {alias}.end_date_jalali < '{JALALI_END_EXCLUSIVE}'"
        )

    def _sql_customer_list(self):
        return (
            f'SELECT DISTINCT b.customer_id AS bill_identity\n'
            f'FROM {self._bill_table()} b\n'
            f'WHERE {self._base_where()}\n'
            f'ORDER BY b.customer_id;'
        )

    def _sql_bill_level(self, group_expr):
        return (
            f'SELECT {group_expr} AS "group",\n'
            f'       COUNT(DISTINCT b.customer_id) AS customer_count\n'
            f'FROM {self._bill_table()} b\n'
            f'WHERE {self._base_where()}\n'
            f'GROUP BY 1\n'
            f'ORDER BY customer_count DESC, "group";'
        )

    def _sql_customer_level(self, group_expr):
        return (
            f'SELECT {group_expr} AS "group",\n'
            f'       COUNT(*) AS customer_count\n'
            f'FROM {self._customer_table()} c\n'
            f'WHERE c.bill_identity IN (\n'
            f'    SELECT DISTINCT b.customer_id\n'
            f'    FROM {self._bill_table()} b\n'
            f'    WHERE {self._base_where()}\n'
            f')\n'
            f'GROUP BY 1\n'
            f'ORDER BY customer_count DESC, "group";'
        )

    def _print_sql(self, sql):
        self.stdout.write('-- Sample PostgreSQL:')
        self.stdout.write(sql)
        self.stdout.write('')

    # ------------------------------------------------------------------ #
    # Request 1
    # ------------------------------------------------------------------ #
    def _print_customer_list(self, customer_ids):
        self._section_header(
            f'Request 1: customers with a bill ending in Khordad/Tir 1405 '
            f'(end_date_jalali in [{JALALI_START}, {JALALI_END_EXCLUSIVE}))'
        )
        self._print_sql(self._sql_customer_list())
        for bill_identity in customer_ids:
            self.stdout.write(str(bill_identity))
        self.stdout.write(self.style.SUCCESS(f'Total: {len(customer_ids)} customers'))

        # customer_ids is built from a set, so every row is unique.
        self._write_csv(
            'request1_customers.csv',
            ['bill_identity'],
            ([bill_identity] for bill_identity in customer_ids),
        )

    # ------------------------------------------------------------------ #
    # Breakdowns
    # ------------------------------------------------------------------ #
    def _print_customer_level_breakdown(self, title, stem, customers, key_fn, show_customers, sql):
        # One customer -> exactly one group, so groups are disjoint.
        groups = defaultdict(set)
        for bill_identity, customer in customers.items():
            groups[key_fn(customer)].add(bill_identity)

        self._section_header(title)
        self._print_sql(sql)
        self._write_groups(groups, len(customers), overlap_possible=False)
        if show_customers:
            self._write_group_members(groups)
        self._export_breakdown(stem, groups, show_customers)

    def _print_bill_level_breakdown(self, title, stem, bill_rows, key_fn, show_customers, sql):
        groups = defaultdict(set)
        for row in bill_rows:
            groups[key_fn(row)].add(row['customer_id'])

        total_customers = len({row['customer_id'] for row in bill_rows})

        self._section_header(title)
        self._print_sql(sql)
        self._write_groups(groups, total_customers, overlap_possible=True)
        if show_customers:
            self._write_group_members(groups)
        self._export_breakdown(stem, groups, show_customers)

    # ------------------------------------------------------------------ #
    # Console output
    # ------------------------------------------------------------------ #
    def _write_groups(self, groups, total, overlap_possible):
        for label, members in self._sorted_groups(groups):
            self.stdout.write(f'{label}: {len(members)}')
        self.stdout.write(self.style.SUCCESS(f'Total unique customers: {total}'))
        if overlap_possible:
            self.stdout.write(
                self.style.WARNING(
                    'Note: group totals may exceed the unique total, since a customer can '
                    'have two bills with different values within this window.'
                )
            )

    def _write_group_members(self, groups):
        for label, members in self._sorted_groups(groups):
            self.stdout.write(f'  -- {label} --')
            for bill_identity in sorted(members):
                self.stdout.write(f'     {bill_identity}')

    def _section_header(self, title):
        self.stdout.write('')
        self.stdout.write('=' * 70)
        self.stdout.write(title)
        self.stdout.write('=' * 70)

    # ------------------------------------------------------------------ #
    # CSV export
    # ------------------------------------------------------------------ #
    @staticmethod
    def _sorted_groups(groups):
        # Biggest group first; label as tie-breaker keeps output deterministic.
        return sorted(groups.items(), key=lambda kv: (-len(kv[1]), str(kv[0])))

    def _export_breakdown(self, stem, groups, show_customers):
        """
        <stem>.csv            -> group, customer_count            (always)
        <stem>_customers.csv  -> group, bill_identity             (only with --show-customers)

        Group members are sets, so no (group, bill_identity) pair can repeat.
        """
        sorted_groups = self._sorted_groups(groups)

        self._write_csv(
            f'{stem}.csv',
            ['group', 'customer_count'],
            ([label, len(members)] for label, members in sorted_groups),
        )

        members_name = f'{stem}_customers.csv'
        if show_customers:
            self._write_csv(
                members_name,
                ['group', 'bill_identity'],
                ([label, bill_identity] for label, members in sorted_groups for bill_identity in sorted(members)),
            )
        else:
            # Don't leave a stale members file behind from an earlier --show-customers run.
            (self.output_dir / members_name).unlink(missing_ok=True)

    def _write_csv(self, filename, header, rows):
        path = self.output_dir / filename
        # "w" truncates, so every run overwrites the previous file.
        with path.open('w', newline='', encoding=CSV_ENCODING) as fh:
            writer = csv.writer(fh)
            writer.writerow(header)
            writer.writerows(rows)
        self.stdout.write(f'Wrote {path}')