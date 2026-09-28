import csv
from collections import defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.billing.models import Bill
from apps.customers.models import Customer

TARGET_CYCLES = ['140503', '140504']
NO_VALUE_LABEL = 'No value / NULL'
DEFAULT_OUTPUT_DIR = 'reports/khordad_tir_1405'

# utf-8-sig adds a BOM so Excel opens Persian text correctly.
CSV_ENCODING = 'utf-8-sig'


class Command(BaseCommand):
    help = (
        'Prints customers with a bill in Khordad/Tir 1405, broken down by several '
        'attributes, and exports each request to its own CSV file.'
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

        bills_qs = Bill.objects.filter(cycle__in=TARGET_CYCLES).values(
            'customer_id',
            'bill_type_name',
            'change_reason_id',
            'change_reason_name',
        )
        self._print_sql('Bills in Khordad/Tir 1405', bills_qs)
        bill_rows = list(bills_qs)

        if not bill_rows:
            self.stdout.write(self.style.WARNING('No bills found for Khordad/Tir 1405.'))
            return

        customer_ids = sorted({row['customer_id'] for row in bill_rows})

        customers_qs = Customer.objects.filter(bill_identity__in=customer_ids)
        self._print_sql('Customers referenced by those bills', customers_qs)
        customers = {c.bill_identity: c for c in customers_qs}

        self._print_customer_list(customer_ids)

        self._print_bill_level_breakdown(
            'Request 2: Bill type (definite / interim / ...)',
            'request2_bill_type',
            bill_rows,
            lambda row: row['bill_type_name'] or NO_VALUE_LABEL,
            show_customers,
        )

        self._print_customer_level_breakdown(
            'Request 3: Faham / Non-Faham',
            'request3_faham',
            customers,
            lambda c: c.subscriber_type or NO_VALUE_LABEL,
            show_customers,
        )

        self._print_customer_level_breakdown(
            'Request 4: Tariff type (usage group)',
            'request4_tariff_type',
            customers,
            lambda c: c.usage_group_name or NO_VALUE_LABEL,
            show_customers,
        )

        self._print_customer_level_breakdown(
            'Request 5: Region office (Omor)',
            'request5_region_office',
            customers,
            lambda c: c.omor_name or NO_VALUE_LABEL,
            show_customers,
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
        )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'CSV files written to: {self.output_dir.resolve()}'))

    # ------------------------------------------------------------------ #
    # Request 1
    # ------------------------------------------------------------------ #
    def _print_customer_list(self, customer_ids):
        self._section_header(f'Request 1: customers with a bill in Khordad/Tir 1405 (cycle in {TARGET_CYCLES})')
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
    def _print_customer_level_breakdown(self, title, stem, customers, key_fn, show_customers):
        # One customer -> exactly one group, so groups are disjoint.
        groups = defaultdict(set)
        for bill_identity, customer in customers.items():
            groups[key_fn(customer)].add(bill_identity)

        self._section_header(title)
        self._write_groups(groups, len(customers), overlap_possible=False)
        if show_customers:
            self._write_group_members(groups)
        self._export_breakdown(stem, groups, show_customers)

    def _print_bill_level_breakdown(self, title, stem, bill_rows, key_fn, show_customers):
        groups = defaultdict(set)
        for row in bill_rows:
            groups[key_fn(row)].add(row['customer_id'])

        total_customers = len({row['customer_id'] for row in bill_rows})

        self._section_header(title)
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

    def _print_sql(self, label, queryset):
        self.stdout.write('')
        self.stdout.write(f'-- SQL for: {label}')
        self.stdout.write(str(queryset.query))

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
