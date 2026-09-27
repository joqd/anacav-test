from django.db import models


class Customer(models.Model):
    class SubscriberType(models.TextChoices):
        FAHAM = "FAHAM", "faham"
        NON_FAHAM = "NON_FAHAM", "non_faham"

    bill_identity = models.BigIntegerField(unique=True, db_index=True)
    subscription_id = models.BigIntegerField(unique=True, null=True, blank=True, db_index=True)
    subscriber_type = models.CharField(
        max_length=10, choices=SubscriberType.choices, null=True, blank=True, db_index=True
    )

    tariff_digit = models.PositiveSmallIntegerField(null=True, blank=True)
    tariff_code = models.CharField(max_length=20, null=True, blank=True, db_index=True)
    tariff_name = models.CharField(max_length=255, null=True, blank=True)

    usage_group_code = models.PositiveSmallIntegerField(null=True, blank=True, db_index=True)
    usage_group_name = models.CharField(max_length=255, null=True, blank=True)
    usage_sub_group_code = models.CharField(max_length=10, null=True, blank=True)
    usage_sub_group_name = models.CharField(max_length=255, null=True, blank=True)

    company_code = models.PositiveSmallIntegerField(null=True, blank=True)
    x_position = models.FloatField(null=True, blank=True)
    y_position = models.FloatField(null=True, blank=True)

    region_code = models.CharField(max_length=10, null=True, blank=True)
    region_name = models.CharField(max_length=255, null=True, blank=True)
    branch_state_code = models.CharField(max_length=10, null=True, blank=True)
    branch_state_name = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    department_code = models.CharField(max_length=10, null=True, blank=True)
    department_name = models.CharField(max_length=255, null=True, blank=True)
    omor_code = models.CharField(max_length=10, null=True, blank=True, db_index=True)
    omor_name = models.CharField(max_length=255, null=True, blank=True, db_index=True)

    contract_power = models.FloatField(null=True, blank=True)
    phase_count = models.PositiveSmallIntegerField(null=True, blank=True)
    amper = models.FloatField(null=True, blank=True)
    voltage = models.CharField(max_length=50, null=True, blank=True)
    counter_type_name = models.CharField(max_length=255, null=True, blank=True)

    national_code = models.CharField(max_length=20, null=True, blank=True)
    mobile = models.CharField(max_length=20, null=True, blank=True)

    install_date_jalali = models.CharField(max_length=10, null=True, blank=True)
    valid_to = models.CharField(max_length=10, null=True, blank=True)

    is_deleted = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)
    dl_insert_time = models.DateTimeField(auto_now_add=True)
    dl_update_time = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "customer"
        verbose_name_plural = "customers"

    def __str__(self):
        return str(self.bill_identity)


class CustomerChangeLog(models.Model):
    class ChangeType(models.IntegerChoices):
        TARIFF_CODE = 2, "tariff code"
        COUNTER_SERIAL_NUMBER = 3, "counter serial number"

    customer = models.ForeignKey(
        Customer,
        to_field="bill_identity",
        db_column="bill_identity",
        on_delete=models.CASCADE,
        related_name="change_logs",
    )

    change_date_jalali = models.CharField(max_length=10)
    change_type_id = models.PositiveSmallIntegerField(choices=ChangeType.choices)
    change_type_name = models.CharField(max_length=100)
    old_value = models.CharField(max_length=255)
    new_value = models.CharField(max_length=255)

    class Meta:
        verbose_name = "customer changelog"
        verbose_name_plural = "customer changelogs"
        ordering = ["customer", "change_date_jalali"]
        indexes = [models.Index(fields=["customer", "change_date_jalali"])]