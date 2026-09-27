from django.db import models

from apps.customers.models import Customer


class Bill(models.Model):
    bill_id = models.BigIntegerField(primary_key=True)
    customer = models.ForeignKey(
        Customer,
        to_field="bill_identity",
        db_column="bill_identity",
        on_delete=models.CASCADE,
        related_name="bills",
    )

    subscriber_type = models.CharField(max_length=10, null=True, blank=True, db_index=True)
    subscription_id = models.BigIntegerField(null=True, blank=True, db_index=True)

    start_date_jalali = models.CharField(max_length=10)
    end_date_jalali = models.CharField(max_length=10)
    cycle = models.CharField(max_length=6, db_index=True)
    duration_days = models.PositiveSmallIntegerField(null=True, blank=True)

    low_kwh = models.FloatField(default=0)
    medium_kwh = models.FloatField(default=0)
    high_kwh = models.FloatField(default=0)
    reactive_low_kwh = models.FloatField(default=0)
    reactive_medium_kwh = models.FloatField(default=0)
    reactive_high_kwh = models.FloatField(default=0)
    friday_low_kwh = models.FloatField(default=0)
    friday_medium_kwh = models.FloatField(default=0)
    friday_high_kwh = models.FloatField(default=0)
    read_power = models.FloatField(null=True, blank=True)

    low_value = models.FloatField(default=0)
    medium_value = models.FloatField(default=0)
    high_value = models.FloatField(default=0)
    debit_value = models.FloatField(default=0)
    toll_value = models.FloatField(default=0)

    canceled_date_jalali = models.CharField(max_length=10, null=True, blank=True)
    emission_date_jalali = models.CharField(max_length=10, null=True, blank=True)
    distribution_date_jalali = models.CharField(max_length=10, null=True, blank=True)

    bill_type_id = models.PositiveSmallIntegerField(db_index=True)
    bill_type_name = models.CharField(max_length=100, null=True, blank=True)

    change_reason_id = models.PositiveSmallIntegerField(null=True, blank=True, db_index=True)
    change_reason_code = models.CharField(max_length=10, null=True, blank=True)
    change_reason_name = models.CharField(max_length=255, null=True, blank=True)

    tariff_code = models.CharField(max_length=20, null=True, blank=True, db_index=True)
    tariff_name = models.CharField(max_length=255, null=True, blank=True)

    last_update_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "bill"
        verbose_name_plural = "bills"
        ordering = ["customer", "start_date_jalali"]

    def __str__(self):
        return f"Bill#{self.bill_id} ({self.customer_id})"

    @property
    def total_kwh(self) -> float:
        return self.low_kwh + self.medium_kwh + self.high_kwh

    @property
    def total_value(self) -> float:
        return self.low_value + self.medium_value + self.high_value


class BillObservation(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name="observations")
    customer = models.ForeignKey(
        Customer,
        to_field="bill_identity",
        db_column="bill_identity",
        on_delete=models.CASCADE,
        related_name="bill_observations",
    )
    observe_id = models.PositiveSmallIntegerField()
    observe_name = models.CharField(max_length=255)
    observe_date_jalali = models.CharField(max_length=10)

    class Meta:
        verbose_name = "bill observation"
        verbose_name_plural = "bill observations"


class MonthlyConsumptionEstimate(models.Model):
    customer = models.ForeignKey(
        Customer,
        to_field="bill_identity",
        db_column="bill_identity",
        on_delete=models.CASCADE,
        related_name="monthly_estimates",
    )
    period_jalali = models.CharField(max_length=7)
    days = models.PositiveSmallIntegerField()

    low_kwh = models.FloatField(default=0)
    medium_kwh = models.FloatField(default=0)
    high_kwh = models.FloatField(default=0)
    friday_low_kwh = models.FloatField(default=0)
    friday_medium_kwh = models.FloatField(default=0)
    friday_high_kwh = models.FloatField(default=0)

    class Meta:
        verbose_name = "monthly consumption estimate"
        verbose_name_plural = "monthly consumption estimates"
        constraints = [
            models.UniqueConstraint(
                fields=["customer", "period_jalali"], name="uniq_customer_period"
            )
        ]
        ordering = ["customer", "period_jalali"]