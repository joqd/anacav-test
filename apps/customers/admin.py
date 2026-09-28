from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import Customer, CustomerChangeLog


class CustomerChangeLogInline(TabularInline):
    model = CustomerChangeLog
    extra = 0
    show_change_link = True


@admin.register(Customer)
class CustomerAdmin(ModelAdmin):
    list_display = (
        'bill_identity',
        'subscription_id',
        'subscriber_type',
        'tariff_code',
        'tariff_name',
        'branch_state_name',
        'omor_name',
        'is_active',
        'is_deleted',
    )
    list_filter = (
        'subscriber_type',
        'is_active',
        'is_deleted',
        'tariff_code',
        'branch_state_name',
        'omor_name',
    )
    search_fields = (
        'bill_identity',
        'subscription_id',
        'national_code',
        'mobile',
        'tariff_code',
        'tariff_name',
        'omor_name',
    )
    readonly_fields = ('dl_insert_time', 'dl_update_time')
    list_per_page = 50
    inlines = (CustomerChangeLogInline,)

    fieldsets = (
        (
            'Identification',
            {
                'fields': (
                    'bill_identity',
                    'subscription_id',
                    'subscriber_type',
                    'national_code',
                    'mobile',
                ),
            },
        ),
        (
            'Tariff and Usage',
            {
                'fields': (
                    'tariff_digit',
                    'tariff_code',
                    'tariff_name',
                    'usage_group_code',
                    'usage_group_name',
                    'usage_sub_group_code',
                    'usage_sub_group_name',
                ),
            },
        ),
        (
            'Location',
            {
                'fields': (
                    'company_code',
                    'x_position',
                    'y_position',
                    'region_code',
                    'region_name',
                    'branch_state_code',
                    'branch_state_name',
                    'department_code',
                    'department_name',
                    'omor_code',
                    'omor_name',
                ),
            },
        ),
        (
            'Electrical Specifications',
            {
                'fields': (
                    'contract_power',
                    'phase_count',
                    'amper',
                    'voltage',
                    'counter_type_name',
                ),
            },
        ),
        (
            'Contract Dates',
            {
                'fields': (
                    'install_date_jalali',
                    'valid_to',
                ),
            },
        ),
        (
            'Status and Timestamps',
            {
                'fields': (
                    'is_active',
                    'is_deleted',
                    'dl_insert_time',
                    'dl_update_time',
                ),
            },
        ),
    )


@admin.register(CustomerChangeLog)
class CustomerChangeLogAdmin(ModelAdmin):
    list_display = (
        'customer',
        'change_date_jalali',
        'change_type_id',
        'change_type_name',
        'old_value',
        'new_value',
    )
    list_filter = ('change_type_id', 'change_date_jalali')
    search_fields = (
        'customer__bill_identity',
        'change_type_name',
        'old_value',
        'new_value',
    )
    list_select_related = ('customer',)
    list_per_page = 50
