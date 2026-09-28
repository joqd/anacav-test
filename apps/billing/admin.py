from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import Bill, BillObservation, MonthlyConsumptionEstimate


class BillObservationInline(TabularInline):
    model = BillObservation
    extra = 0
    show_change_link = True


@admin.register(Bill)
class BillAdmin(ModelAdmin):
    list_display = (
        'bill_id',
        'customer',
        'cycle',
        'start_date_jalali',
        'end_date_jalali',
        'bill_type_id',
        'total_kwh',
        'total_value',
        'tariff_code',
    )
    list_filter = (
        'cycle',
        'bill_type_id',
        'change_reason_id',
        'tariff_code',
        'subscriber_type',
    )
    search_fields = (
        'bill_id',
        'customer__bill_identity',
        'subscription_id',
        'cycle',
        'tariff_code',
        'tariff_name',
    )
    list_select_related = ('customer',)
    list_per_page = 50
    inlines = (BillObservationInline,)

    @admin.display(description='Total consumption', ordering='low_kwh')
    def total_kwh(self, obj):
        return obj.total_kwh

    @admin.display(description='Total value')
    def total_value(self, obj):
        return obj.total_value

    fieldsets = (
        (
            'Identification',
            {
                'fields': (
                    'bill_id',
                    'customer',
                    'subscriber_type',
                    'subscription_id',
                    'cycle',
                    'bill_type_id',
                    'bill_type_name',
                ),
            },
        ),
        (
            'Billing Period',
            {
                'fields': (
                    'start_date_jalali',
                    'end_date_jalali',
                    'duration_days',
                    'canceled_date_jalali',
                    'emission_date_jalali',
                    'distribution_date_jalali',
                ),
            },
        ),
        (
            'Consumption (kWh)',
            {
                'fields': (
                    'low_kwh',
                    'medium_kwh',
                    'high_kwh',
                    'reactive_low_kwh',
                    'reactive_medium_kwh',
                    'reactive_high_kwh',
                    'friday_low_kwh',
                    'friday_medium_kwh',
                    'friday_high_kwh',
                    'read_power',
                ),
            },
        ),
        (
            'Amounts',
            {
                'fields': (
                    'low_value',
                    'medium_value',
                    'high_value',
                    'debit_value',
                    'toll_value',
                ),
            },
        ),
        (
            'Change Reason and Tariff',
            {
                'fields': (
                    'change_reason_id',
                    'change_reason_code',
                    'change_reason_name',
                    'tariff_code',
                    'tariff_name',
                ),
            },
        ),
        (
            'Metadata',
            {
                'fields': ('last_update_time',),
            },
        ),
    )


@admin.register(BillObservation)
class BillObservationAdmin(ModelAdmin):
    list_display = (
        'bill',
        'customer',
        'observe_id',
        'observe_name',
        'observe_date_jalali',
    )
    list_filter = ('observe_id', 'observe_date_jalali')
    search_fields = (
        'bill__bill_id',
        'customer__bill_identity',
        'observe_name',
    )
    list_select_related = ('bill', 'customer')
    list_per_page = 50


@admin.register(MonthlyConsumptionEstimate)
class MonthlyConsumptionEstimateAdmin(ModelAdmin):
    list_display = (
        'customer',
        'period_jalali',
        'days',
        'low_kwh',
        'medium_kwh',
        'high_kwh',
        'friday_low_kwh',
        'friday_medium_kwh',
        'friday_high_kwh',
    )
    list_filter = ('period_jalali',)
    search_fields = ('customer__bill_identity', 'period_jalali')
    list_select_related = ('customer',)
    list_per_page = 50
