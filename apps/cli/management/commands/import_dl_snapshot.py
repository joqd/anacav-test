import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.billing.models import Bill, MonthlyConsumptionEstimate
from apps.customers.models import Customer
from apps.metering.models import MeasurementTool, SmartMeterReading


def blank_to_none(value):
    if value is None:
        return None
    value = value.strip()
    return value or None


def to_float(value):
    value = blank_to_none(value)
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def to_int(value):
    value = to_float(value)
    return int(value) if value is not None else None


def to_bool_tf(value):
    value = blank_to_none(value)
    if value is None:
        return None
    return value.lower() in ("t", "true", "1", "yes")


def parse_dt(value):
    value = blank_to_none(value)
    if value is None:
        return None
    dt = parse_datetime(value)
    if dt is None:
        return None
    if settings.USE_TZ and timezone.is_naive(dt):
        dt = timezone.make_aware(dt)
    return dt


def open_csv(path):
    return open(path, encoding="utf-8-sig", newline="")


class Command(BaseCommand):
    help = "Imports the DL/Faham CSV snapshot into Customer, Bill, MonthlyConsumptionEstimate and MeasurementTool/SmartMeterReading."

    def add_arguments(self, parser):
        parser.add_argument("--data-dir", default="./assets")
        parser.add_argument("--faham-customers", default="faham_customer_full.csv")
        parser.add_argument("--non-faham-customers", default="non_faham_customer_full.csv")
        parser.add_argument("--bills", default="bill_tb_bill_1405_to_present.csv")
        parser.add_argument("--monthly", default="normal_customer_monthly_1405_to_present.csv")
        parser.add_argument("--meters", default="faham_meter.csv")
        parser.add_argument("--meter-readings", default="faham_meterinfo_1405_to_present.csv")
        parser.add_argument("--skip-readings", action="store_true")
        parser.add_argument("--reading-limit", type=int, default=None)

    def handle(self, *args, **options):
        data_dir = options["data_dir"]

        self.import_customers(os.path.join(data_dir, options["faham_customers"]))
        self.import_customers(os.path.join(data_dir, options["non_faham_customers"]))

        self.import_bills(os.path.join(data_dir, options["bills"]))
        self.import_monthly(os.path.join(data_dir, options["monthly"]))
        self.import_meters(os.path.join(data_dir, options["meters"]))

        if not options["skip_readings"]:
            self.import_meter_readings(
                os.path.join(data_dir, options["meter_readings"]), options["reading_limit"]
            )

    def import_customers(self, path):
        self.stdout.write(f"Importing customers from {path}")
        created, updated, skipped = 0, 0, 0

        with open_csv(path) as f:
            reader = csv.DictReader(f)
            with transaction.atomic():
                for i, row in enumerate(reader, start=1):
                    bill_identity = to_int(row["xsubscriptionbillid"])
                    if bill_identity is None:
                        skipped += 1
                        continue

                    is_active = to_bool_tf(row["xsubscriberisactive"])
                    if is_active is None:
                        is_active = True

                    tariff_code = blank_to_none(row["xtariffcode"])
                    tariff_digit = None
                    if tariff_code and tariff_code[-1].isdigit():
                        tariff_digit = int(tariff_code[-1])

                    defaults = dict(
                        subscription_id=to_int(row["xsubscriptionid_pk"]),
                        subscriber_type=blank_to_none(row["subscriber_type"]),
                        tariff_digit=tariff_digit,
                        tariff_code=tariff_code,
                        tariff_name=blank_to_none(row["xtariffname"]),
                        usage_group_code=to_int(row["xusagegroupcode"]),
                        usage_group_name=blank_to_none(row["xusagegroupname"]),
                        usage_sub_group_code=blank_to_none(row["xusagesubgroupcode"]),
                        usage_sub_group_name=blank_to_none(row["xusagesubgroupname"]),
                        x_position=to_float(row["xlongitude"]),
                        y_position=to_float(row["xlatitude"]),
                        region_code=blank_to_none(row["xregioncode"]),
                        region_name=blank_to_none(row["xregionname"]),
                        branch_state_code=blank_to_none(row["xbranchstatecode"]),
                        branch_state_name=blank_to_none(row["xbranchstatename"]),
                        department_code=blank_to_none(row["xdepartmentcode"]),
                        department_name=blank_to_none(row["xdepartmentname"]),
                        omor_code=blank_to_none(row["xomorcode"]),
                        omor_name=blank_to_none(row["xomorname"]),
                        contract_power=to_float(row["xcontractpower"]),
                        phase_count=to_int(row["xfaze"]),
                        amper=to_float(row["xamper"]),
                        voltage=blank_to_none(row["xvoltage"]),
                        counter_type_name=blank_to_none(row["xcountertypename"]),
                        national_code=blank_to_none(row["xsubscribernationalcode"]),
                        mobile=blank_to_none(row["xsubscribermobile"])
                        or blank_to_none(row.get("xConsumerMobile")),
                        install_date_jalali=blank_to_none(row["xinstalldate"]),
                        valid_to=blank_to_none(row["xexpiredate"])
                        or blank_to_none(row["xreduceexpiredate"]),
                        is_active=is_active,
                        is_deleted=not is_active,
                    )

                    _, was_created = Customer.objects.update_or_create(
                        bill_identity=bill_identity, defaults=defaults
                    )
                    created += was_created
                    updated += not was_created

                    if i % 1000 == 0:
                        self.stdout.write(f"  ... {i} rows processed")

        self.stdout.write(
            self.style.SUCCESS(
                f"Customers: {created} created, {updated} updated, {skipped} skipped (no bill_identity)"
            )
        )

    def import_bills(self, path):
        self.stdout.write(f"Importing bills from {path}")
        known_identities = set(Customer.objects.values_list("bill_identity", flat=True))
        created, updated, skipped = 0, 0, 0

        with open_csv(path) as f:
            reader = csv.DictReader(f)
            with transaction.atomic():
                for i, row in enumerate(reader, start=1):
                    bill_id = to_int(row["xBillId_pk"])
                    bill_identity = to_int(row["xBillIdentity"])

                    if bill_id is None or bill_identity is None or bill_identity not in known_identities:
                        skipped += 1
                        continue

                    start_date = blank_to_none(row["xBillStartDate"])
                    cycle = start_date.replace("/", "")[:6] if start_date else ""

                    defaults = dict(
                        customer_id=bill_identity,
                        subscriber_type=blank_to_none(row["subscriber_type"]),
                        subscription_id=to_int(row["xSubscriptionId_fk"]),
                        start_date_jalali=start_date or "",
                        end_date_jalali=blank_to_none(row["xBillEndDate"]) or "",
                        cycle=cycle,
                        duration_days=to_int(row["xBillDayNum"]),
                        low_kwh=to_float(row["xLowKw"]) or 0,
                        medium_kwh=to_float(row["xMeduimKw"]) or 0,
                        high_kwh=to_float(row["xHighKw"]) or 0,
                        reactive_low_kwh=to_float(row["xReactiveLowKw"]) or 0,
                        reactive_medium_kwh=to_float(row["xReactiveMeduimKw"]) or 0,
                        reactive_high_kwh=to_float(row["xReactiveHighKw"]) or 0,
                        friday_low_kwh=to_float(row["xFridayLowKw"]) or 0,
                        friday_medium_kwh=to_float(row["xFridayMeduimKw"]) or 0,
                        friday_high_kwh=to_float(row["xFridayHighKw"]) or 0,
                        read_power=to_float(row["xReadPower"]),
                        low_value=to_float(row["xLowValue"]) or 0,
                        medium_value=to_float(row["xMeduimValue"]) or 0,
                        high_value=to_float(row["xHighValue"]) or 0,
                        debit_value=to_float(row["xDebitValue"]) or 0,
                        toll_value=to_float(row["xTollValue"]) or 0,
                        canceled_date_jalali=blank_to_none(row["xBillRescissionDate"]),
                        emission_date_jalali=blank_to_none(row["xEmissionDate"]),
                        distribution_date_jalali=blank_to_none(row["xDistributionDate"]),
                        bill_type_id=to_int(row["xBillTypeId_fk"]) or 0,
                        bill_type_name=blank_to_none(row["xBillTypeName"]),
                        change_reason_id=to_int(row["xBillChangingReasonId_fk"]),
                        change_reason_code=blank_to_none(row["xBillChangingReasonCode"]),
                        change_reason_name=blank_to_none(row["xBillChangingReasonName"]),
                        tariff_code=blank_to_none(row["xTariffCode"]),
                        tariff_name=blank_to_none(row["xTariffName"]),
                        last_update_time=parse_dt(row["lastUpdateTime"]),
                    )

                    _, was_created = Bill.objects.update_or_create(bill_id=bill_id, defaults=defaults)
                    created += was_created
                    updated += not was_created

                    if i % 1000 == 0:
                        self.stdout.write(f"  ... {i} rows processed")

        self.stdout.write(
            self.style.SUCCESS(
                f"Bills: {created} created, {updated} updated, {skipped} skipped (unresolved customer)"
            )
        )

    def import_monthly(self, path):
        self.stdout.write(f"Importing monthly consumption estimates from {path}")
        sub_to_identity = dict(
            Customer.objects.exclude(subscription_id__isnull=True).values_list(
                "subscription_id", "bill_identity"
            )
        )
        created, updated, skipped = 0, 0, 0

        with open_csv(path) as f:
            reader = csv.DictReader(f)
            with transaction.atomic():
                for i, row in enumerate(reader, start=1):
                    subscription_id = to_int(row["subscriptionId"])
                    bill_identity = sub_to_identity.get(subscription_id)
                    period = blank_to_none(row["date"])

                    if bill_identity is None or period is None:
                        skipped += 1
                        continue

                    defaults = dict(
                        days=to_int(row["duration"]) or 0,
                        low_kwh=to_float(row["valueLowKWH"]) or 0,
                        medium_kwh=to_float(row["valueMediumKWH"]) or 0,
                        high_kwh=to_float(row["valueHighKWH"]) or 0,
                    )

                    _, was_created = MonthlyConsumptionEstimate.objects.update_or_create(
                        customer_id=bill_identity, period_jalali=period, defaults=defaults
                    )
                    created += was_created
                    updated += not was_created

                    if i % 1000 == 0:
                        self.stdout.write(f"  ... {i} rows processed")

        self.stdout.write(
            self.style.SUCCESS(
                f"Monthly estimates: {created} created, {updated} updated, {skipped} skipped (unresolved customer)"
            )
        )

    def import_meters(self, path):
        self.stdout.write(f"Importing measurement tools from {path}")
        sub_to_identity = dict(
            Customer.objects.exclude(subscription_id__isnull=True).values_list(
                "subscription_id", "bill_identity"
            )
        )
        created, updated, skipped = 0, 0, 0

        with open_csv(path) as f:
            reader = csv.DictReader(f)
            with transaction.atomic():
                for i, row in enumerate(reader, start=1):
                    meter_id = to_int(row["MeterId"])
                    if meter_id is None:
                        skipped += 1
                        continue

                    bill_identity = sub_to_identity.get(to_int(row["SubscriptionId"]))

                    defaults = dict(
                        serial_number=blank_to_none(row["MeterName"]) or "",
                        tool_name=blank_to_none(row["MeterName"]) or "",
                        tool_type_id=to_int(row["MeterType"]),
                        customer_id=bill_identity,
                        active_status=blank_to_none(row["State"]) == "فعال",
                        ct_ratio=to_int(row["CT"]) or 1,
                        pt_ratio=to_int(row["PT"]) or 1,
                        mv_feeder_id=blank_to_none(row["MVFeederID"]),
                        contract_power=to_float(row["ContractPower"]),
                        branch_state_code=blank_to_none(row["BranchStateCode"]),
                        branch_state_name=blank_to_none(row["BranchStateName"]),
                        zone_name=blank_to_none(row["ZoneName"]),
                        department_name=blank_to_none(row["DepartmentName"]),
                        remote_control_type=blank_to_none(row["RemoteControlType"]),
                        usage_type_id=blank_to_none(row["UsageTypeId"]),
                    )

                    _, was_created = MeasurementTool.objects.update_or_create(
                        meter_id=meter_id, defaults=defaults
                    )
                    created += was_created
                    updated += not was_created

                    if i % 1000 == 0:
                        self.stdout.write(f"  ... {i} rows processed")

        self.stdout.write(
            self.style.SUCCESS(f"Measurement tools: {created} created, {updated} updated, {skipped} skipped")
        )

    def import_meter_readings(self, path, limit):
        self.stdout.write(f"Importing meter readings from {path}")
        tool_cache = dict(MeasurementTool.objects.values_list("meter_id", "id"))
        created, updated, skipped = 0, 0, 0

        with open_csv(path) as f:
            reader = csv.DictReader(f)
            with transaction.atomic():
                for i, row in enumerate(reader, start=1):
                    if limit and i > limit:
                        break

                    meter_id = to_int(row["MeterID"])
                    tool_pk = tool_cache.get(meter_id)
                    time_tag = to_int(row["TimeTag"])
                    reading_time = parse_dt(row["Date"])

                    if tool_pk is None or time_tag is None or reading_time is None:
                        skipped += 1
                        continue

                    defaults = dict(
                        reading_time=reading_time,
                        shamsi_date=blank_to_none(row["ShamsiDate"]),
                        meter_serial_number=blank_to_none(row["MeterSerialNumber"]),
                        power_active=to_float(row["PowerActive"]),
                        power_reactive=to_float(row["PowerReactive"]),
                        power_factor=to_float(row["PowerFactor"]),
                        demand=to_float(row["demand"]),
                        frequency=to_float(row["Frequency"]),
                        active_energy=to_float(row["ActiveEnergy"]),
                        reactive_energy=to_float(row["ReactiveEnergy"]),
                        active_energy_export=to_float(row["ActiveEnergyExport"]),
                        reactive_energy_export=to_float(row["ReActiveEnergyExport"]),
                        voltage_phase_a=to_float(row["VoltagePhaseA"]),
                        voltage_phase_b=to_float(row["VoltagePhaseB"]),
                        voltage_phase_c=to_float(row["VoltagePhaseC"]),
                        voltage_phase_n=to_float(row["VoltagePhaseN"]),
                        current_phase_a=to_float(row["CurrentPhaseA"]),
                        current_phase_b=to_float(row["CurrentPhaseB"]),
                        current_phase_c=to_float(row["CurrentPhaseC"]),
                        current_phase_n=to_float(row["CurrentPhaseN"]),
                    )

                    _, was_created = SmartMeterReading.objects.update_or_create(
                        tool_id=tool_pk, time_tag=time_tag, defaults=defaults
                    )
                    created += was_created
                    updated += not was_created

                    if i % 2000 == 0:
                        self.stdout.write(f"  ... {i} rows processed")

        self.stdout.write(
            self.style.SUCCESS(
                f"Meter readings: {created} created, {updated} updated, {skipped} skipped (unknown meter/time)"
            )
        )