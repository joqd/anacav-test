from django.db import models

from apps.customers.models import Customer


class MeteringStation(models.Model):
    station_id = models.BigIntegerField(unique=True)
    station_name = models.CharField(max_length=255)
    station_type_id = models.PositiveSmallIntegerField()

    def __str__(self):
        return self.station_name


class MeasurementTool(models.Model):
    pgds_code = models.CharField(max_length=20, unique=True, null=True, blank=True, db_index=True)
    meter_id = models.BigIntegerField(unique=True, db_index=True)
    serial_number = models.CharField(max_length=50, blank=True)
    tool_id = models.BigIntegerField(unique=True, null=True, blank=True)
    tool_name = models.CharField(max_length=100, blank=True)
    tool_type_id = models.PositiveSmallIntegerField(null=True, blank=True)

    station = models.ForeignKey(MeteringStation, on_delete=models.SET_NULL, null=True, blank=True, related_name='tools')
    customer = models.ForeignKey(
        Customer,
        to_field='bill_identity',
        db_column='bill_identity',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='measurement_tools',
    )

    active_status = models.BooleanField(default=True)
    formula_type_id = models.PositiveSmallIntegerField(null=True, blank=True)
    formula_mount_date = models.DateTimeField(null=True, blank=True)
    formula_dismount_date = models.DateTimeField(null=True, blank=True)

    ct_ratio = models.PositiveIntegerField(default=1)
    pt_ratio = models.PositiveIntegerField(default=1)

    mv_feeder_id = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    contract_power = models.FloatField(null=True, blank=True)
    branch_state_code = models.CharField(max_length=10, null=True, blank=True)
    branch_state_name = models.CharField(max_length=255, null=True, blank=True)
    zone_name = models.CharField(max_length=255, null=True, blank=True)
    department_name = models.CharField(max_length=255, null=True, blank=True)
    remote_control_type = models.CharField(max_length=100, null=True, blank=True)
    usage_type_id = models.CharField(max_length=20, null=True, blank=True)

    subscription_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    faham_unit_id = models.CharField(max_length=50, null=True, blank=True)
    unit_id = models.PositiveIntegerField(null=True, blank=True)
    billing_unit_id = models.PositiveIntegerField(null=True, blank=True)
    x_position = models.FloatField(null=True, blank=True)
    y_position = models.FloatField(null=True, blank=True)
    category = models.CharField(max_length=50, null=True, blank=True)
    sub_category = models.CharField(max_length=50, null=True, blank=True)
    state = models.CharField(max_length=50, null=True, blank=True)
    department_code = models.CharField(max_length=20, null=True, blank=True)
    usage_group_code = models.PositiveSmallIntegerField(null=True, blank=True)
    usage_group_name = models.CharField(max_length=100, null=True, blank=True)
    is_building = models.BooleanField(null=True, blank=True)
    voltage_str = models.CharField(max_length=20, null=True, blank=True)
    identity_number = models.CharField(max_length=50, null=True, blank=True)
    zone_id = models.CharField(max_length=50, null=True, blank=True)
    customer_zone_id = models.CharField(max_length=50, null=True, blank=True)
    customer_zone_name = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f'{self.tool_name} ({self.meter_id})'

    @property
    def multiplier(self) -> int:
        return self.ct_ratio * self.pt_ratio


class FeederCustomerLink(models.Model):
    customer = models.ForeignKey(
        Customer,
        to_field='bill_identity',
        db_column='bill_identity',
        on_delete=models.CASCADE,
        related_name='feeder_links',
    )
    tool = models.ForeignKey(MeasurementTool, on_delete=models.CASCADE, related_name='connected_customers')
    legacy_customer_id = models.BigIntegerField(db_index=True)

    last_update = models.DateTimeField()
    valid_to = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=['tool', 'is_deleted'])]
        constraints = [models.UniqueConstraint(fields=['customer', 'tool'], name='uniq_customer_tool_link')]


class ToolPowerDailyStat(models.Model):
    tool = models.ForeignKey(MeasurementTool, on_delete=models.CASCADE, related_name='power_stats')
    sample_date = models.DateField()

    sample_count = models.PositiveIntegerField()
    first_time = models.DateTimeField()
    last_time = models.DateTimeField()
    avg_power = models.FloatField()
    min_power = models.FloatField()
    max_power = models.FloatField()
    sum_power = models.FloatField()
    active_status_count = models.PositiveIntegerField()
    formula_type_count = models.PositiveIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['tool', 'sample_date'], name='uniq_tool_power_day')]


class MeterQuarterlyEnergy(models.Model):
    tool = models.ForeignKey(MeasurementTool, on_delete=models.CASCADE, related_name='quarterly_energy')
    sample_date = models.DateField()

    sample_count = models.PositiveIntegerField()
    first_time = models.DateTimeField()
    last_time = models.DateTimeField()

    sum_active_energy_export = models.FloatField(default=0)
    sum_active_energy_import = models.FloatField(default=0)
    sum_reactive_energy_export = models.FloatField(default=0)
    sum_reactive_energy_import = models.FloatField(default=0)
    avg_active_energy_export = models.FloatField(default=0)
    max_active_energy_export = models.FloatField(default=0)

    meter_count = models.PositiveIntegerField()
    status_nonnull_count = models.PositiveIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['tool', 'sample_date'], name='uniq_tool_quarter_day')]


class SmartMeterReading(models.Model):
    tool = models.ForeignKey(MeasurementTool, on_delete=models.CASCADE, related_name='readings')
    time_tag = models.BigIntegerField(db_index=True)
    reading_time = models.DateTimeField(db_index=True)
    shamsi_date = models.CharField(max_length=19, null=True, blank=True)
    meter_serial_number = models.CharField(max_length=50, null=True, blank=True)

    power_active = models.FloatField(null=True, blank=True)
    power_reactive = models.FloatField(null=True, blank=True)
    power_factor = models.FloatField(null=True, blank=True)
    demand = models.FloatField(null=True, blank=True)
    frequency = models.FloatField(null=True, blank=True)

    active_energy = models.FloatField(null=True, blank=True)
    reactive_energy = models.FloatField(null=True, blank=True)
    active_energy_export = models.FloatField(null=True, blank=True)
    reactive_energy_export = models.FloatField(null=True, blank=True)

    voltage_phase_a = models.FloatField(null=True, blank=True)
    voltage_phase_b = models.FloatField(null=True, blank=True)
    voltage_phase_c = models.FloatField(null=True, blank=True)
    voltage_phase_n = models.FloatField(null=True, blank=True)
    current_phase_a = models.FloatField(null=True, blank=True)
    current_phase_b = models.FloatField(null=True, blank=True)
    current_phase_c = models.FloatField(null=True, blank=True)
    current_phase_n = models.FloatField(null=True, blank=True)

    phase_a_angle = models.FloatField(null=True, blank=True)
    phase_b_angle = models.FloatField(null=True, blank=True)
    phase_c_angle = models.FloatField(null=True, blank=True)
    phase_n_angle = models.FloatField(null=True, blank=True)

    voltage_l1 = models.FloatField(null=True, blank=True)
    voltage_l2 = models.FloatField(null=True, blank=True)
    voltage_l3 = models.FloatField(null=True, blank=True)
    current_l1 = models.FloatField(null=True, blank=True)
    current_l2 = models.FloatField(null=True, blank=True)
    current_l3 = models.FloatField(null=True, blank=True)

    guid = models.CharField(max_length=64, null=True, blank=True)
    source_id = models.CharField(max_length=50, null=True, blank=True)
    source_name = models.CharField(max_length=50, null=True, blank=True)
    profile_status_energy = models.IntegerField(null=True, blank=True)
    profile_status_power = models.IntegerField(null=True, blank=True)
    dl_insert_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['tool', 'reading_time']
        indexes = [models.Index(fields=['tool', 'reading_time'])]
        constraints = [models.UniqueConstraint(fields=['tool', 'time_tag'], name='uniq_tool_time_tag')]
