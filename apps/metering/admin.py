from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import (
    FeederCustomerLink,
    MeasurementTool,
    MeteringStation,
    MeterQuarterlyEnergy,
    SmartMeterReading,
    ToolPowerDailyStat,
)


class MeasurementToolInline(TabularInline):
    model = MeasurementTool
    extra = 0
    show_change_link = True


class FeederCustomerLinkInline(TabularInline):
    model = FeederCustomerLink
    extra = 0
    show_change_link = True


class ToolPowerDailyStatInline(TabularInline):
    model = ToolPowerDailyStat
    extra = 0
    show_change_link = True


class MeterQuarterlyEnergyInline(TabularInline):
    model = MeterQuarterlyEnergy
    extra = 0
    show_change_link = True


@admin.register(MeteringStation)
class MeteringStationAdmin(ModelAdmin):
    list_display = (
        'station_id',
        'station_name',
        'station_type_id',
    )
    list_filter = ('station_type_id',)
    search_fields = ('station_id', 'station_name')
    list_per_page = 50
    inlines = (MeasurementToolInline,)


@admin.register(MeasurementTool)
class MeasurementToolAdmin(ModelAdmin):
    list_display = (
        'meter_id',
        'tool_name',
        'serial_number',
        'pgds_code',
        'station',
        'customer',
        'active_status',
        'multiplier',
    )
    list_filter = (
        'active_status',
        'tool_type_id',
        'formula_type_id',
        'station',
        'branch_state_name',
        'zone_name',
    )
    search_fields = (
        'meter_id',
        'pgds_code',
        'serial_number',
        'tool_id',
        'tool_name',
        'customer__bill_identity',
        'mv_feeder_id',
    )
    list_select_related = ('station', 'customer')
    list_per_page = 50
    inlines = (
        FeederCustomerLinkInline,
        ToolPowerDailyStatInline,
        MeterQuarterlyEnergyInline,
    )

    @admin.display(description='Multiplier')
    def multiplier(self, obj):
        return obj.multiplier

    fieldsets = (
        (
            'Identification',
            {
                'fields': (
                    'meter_id',
                    'pgds_code',
                    'serial_number',
                    'tool_id',
                    'tool_name',
                    'tool_type_id',
                ),
            },
        ),
        (
            'Relationships',
            {
                'fields': ('station', 'customer'),
            },
        ),
        (
            'Status and Formula',
            {
                'fields': (
                    'active_status',
                    'formula_type_id',
                    'formula_mount_date',
                    'formula_dismount_date',
                ),
            },
        ),
        (
            'Electrical Configuration',
            {
                'fields': ('ct_ratio', 'pt_ratio'),
            },
        ),
        (
            'Location and Contract',
            {
                'fields': (
                    'mv_feeder_id',
                    'contract_power',
                    'branch_state_code',
                    'branch_state_name',
                    'zone_name',
                    'department_name',
                    'remote_control_type',
                    'usage_type_id',
                ),
            },
        ),
    )


@admin.register(FeederCustomerLink)
class FeederCustomerLinkAdmin(ModelAdmin):
    list_display = (
        'customer',
        'tool',
        'legacy_customer_id',
        'last_update',
        'valid_to',
        'is_deleted',
    )
    list_filter = ('is_deleted', 'last_update', 'valid_to')
    search_fields = (
        'customer__bill_identity',
        'tool__meter_id',
        'tool__serial_number',
        'legacy_customer_id',
    )
    list_select_related = ('customer', 'tool')
    list_per_page = 50


@admin.register(ToolPowerDailyStat)
class ToolPowerDailyStatAdmin(ModelAdmin):
    list_display = (
        'tool',
        'sample_date',
        'sample_count',
        'avg_power',
        'min_power',
        'max_power',
        'sum_power',
        'active_status_count',
        'formula_type_count',
    )
    list_filter = ('sample_date',)
    search_fields = ('tool__meter_id', 'tool__serial_number')
    list_select_related = ('tool',)
    list_per_page = 50
    date_hierarchy = 'sample_date'


@admin.register(MeterQuarterlyEnergy)
class MeterQuarterlyEnergyAdmin(ModelAdmin):
    list_display = (
        'tool',
        'sample_date',
        'sample_count',
        'sum_active_energy_import',
        'sum_active_energy_export',
        'sum_reactive_energy_import',
        'sum_reactive_energy_export',
        'meter_count',
        'status_nonnull_count',
    )
    list_filter = ('sample_date',)
    search_fields = ('tool__meter_id', 'tool__serial_number')
    list_select_related = ('tool',)
    list_per_page = 50
    date_hierarchy = 'sample_date'


@admin.register(SmartMeterReading)
class SmartMeterReadingAdmin(ModelAdmin):
    list_display = (
        'tool',
        'reading_time',
        'shamsi_date',
        'power_active',
        'power_reactive',
        'power_factor',
        'demand',
        'active_energy',
    )
    list_filter = ('reading_time',)
    search_fields = (
        'tool__meter_id',
        'tool__serial_number',
        'meter_serial_number',
        'shamsi_date',
    )
    list_select_related = ('tool',)
    list_per_page = 100
    date_hierarchy = 'reading_time'
