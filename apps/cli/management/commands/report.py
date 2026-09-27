from collections import defaultdict

from django.core.management.base import BaseCommand

from apps.billing.models import Bill
from apps.customers.models import Customer

TARGET_CYCLES = ["140503", "140504"]
NO_VALUE_LABEL = "No value / NULL"


class Command(BaseCommand):
    help = "Prints customers with a bill in Khordad/Tir 1405, broken down by several attributes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--show-customers",
            action="store_true",
            help="Also list the bill_identity values inside every breakdown group.",
        )

    def handle(self, *args, **options):
        show_customers = options["show_customers"]

        bills_qs = Bill.objects.filter(cycle__in=TARGET_CYCLES).values(
            "customer_id",
            "bill_type_name",
            "change_reason_id",
            "change_reason_name",
        )
        self._print_sql("Bills in Khordad/Tir 1405", bills_qs)
        bill_rows = list(bills_qs)

        if not bill_rows:
            self.stdout.write(self.style.WARNING("No bills found for Khordad/Tir 1405."))
            return

        customer_ids = sorted({row["customer_id"] for row in bill_rows})

        customers_qs = Customer.objects.filter(bill_identity__in=customer_ids)
        self._print_sql("Customers referenced by those bills", customers_qs)
        customers = {c.bill_identity: c for c in customers_qs}

        self._print_customer_list(customer_ids)

        self._print_bill_level_breakdown(
            "Request 2: Bill type (definite / interim / ...)",
            bill_rows,
            lambda row: row["bill_type_name"] or NO_VALUE_LABEL,
            show_customers,
        )

        self._print_customer_level_breakdown(
            "Request 3: Faham / Non-Faham",
            customers,
            lambda c: c.subscriber_type or NO_VALUE_LABEL,
            show_customers,
        )

        self._print_customer_level_breakdown(
            "Request 4: Tariff type (usage group)",
            customers,
            lambda c: c.usage_group_name or NO_VALUE_LABEL,
            show_customers,
        )

        self._print_customer_level_breakdown(
            "Request 5: Region office (Omor)",
            customers,
            lambda c: c.omor_name or NO_VALUE_LABEL,
            show_customers,
        )

        self._print_bill_level_breakdown(
            "Request 6: Agent observe code (Shahed code)",
            bill_rows,
            lambda row: (
                f"{row['change_reason_id']} - {row['change_reason_name']}"
                if row["change_reason_id"] is not None
                else NO_VALUE_LABEL
            ),
            show_customers,
        )

    def _print_customer_list(self, customer_ids):
        self._section_header(
            f"Request 1: customers with a bill in Khordad/Tir 1405 (cycle in {TARGET_CYCLES})"
        )
        for bill_identity in customer_ids:
            self.stdout.write(str(bill_identity))
        self.stdout.write(self.style.SUCCESS(f"Total: {len(customer_ids)} customers"))

    def _print_customer_level_breakdown(self, title, customers, key_fn, show_customers):
        groups = defaultdict(list)
        for bill_identity, customer in customers.items():
            groups[key_fn(customer)].append(bill_identity)

        self._section_header(title)
        self._write_groups(groups, len(customers), overlap_possible=False)
        if show_customers:
            self._write_group_members(groups)

    def _print_bill_level_breakdown(self, title, bill_rows, key_fn, show_customers):
        groups = defaultdict(set)
        for row in bill_rows:
            groups[key_fn(row)].add(row["customer_id"])

        total_customers = len({row["customer_id"] for row in bill_rows})

        self._section_header(title)
        self._write_groups(groups, total_customers, overlap_possible=True)
        if show_customers:
            self._write_group_members(groups)

    def _write_groups(self, groups, total, overlap_possible):
        for label, members in sorted(groups.items(), key=lambda kv: len(kv[1]), reverse=True):
            self.stdout.write(f"{label}: {len(members)}")
        self.stdout.write(self.style.SUCCESS(f"Total unique customers: {total}"))
        if overlap_possible:
            self.stdout.write(
                self.style.WARNING(
                    "Note: group totals may exceed the unique total, since a customer can "
                    "have two bills with different values within this window."
                )
            )

    def _write_group_members(self, groups):
        for label, members in sorted(groups.items(), key=lambda kv: len(kv[1]), reverse=True):
            self.stdout.write(f"  -- {label} --")
            for bill_identity in sorted(members):
                self.stdout.write(f"     {bill_identity}")

    def _section_header(self, title):
        self.stdout.write("")
        self.stdout.write("=" * 70)
        self.stdout.write(title)
        self.stdout.write("=" * 70)

    def _print_sql(self, label, queryset):
        self.stdout.write("")
        self.stdout.write(f"-- SQL for: {label}")
        self.stdout.write(str(queryset.query))