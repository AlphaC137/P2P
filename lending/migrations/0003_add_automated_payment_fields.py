from django.db import migrations, models
from decimal import Decimal
from django.db.utils import OperationalError


def check_column_exists(apps, schema_editor, table_name, column_name):
    db_alias = schema_editor.connection.alias
    try:
        with schema_editor.connection.cursor() as cursor:
            cursor.execute(
                f"SELECT COUNT({column_name}) FROM {table_name} LIMIT 1"
            )
            # If we get here, the column exists
            return True
    except OperationalError:
        # Column doesn't exist
        return False


class Migration(migrations.Migration):

    dependencies = [
        ('lending', '0002_loan_borrower_verified_loan_collateral_description_and_more'),
    ]

    operations = [
        migrations.RunPython(
            lambda apps, schema_editor: None if check_column_exists(
                apps, schema_editor, 'lending_loanpayment', 'reminder_sent'
            ) else migrations.AddField(
                model_name='loanpayment',
                name='reminder_sent',
                field=models.BooleanField(default=False),
            ).database_forwards(
                'lending', schema_editor, 
                apps.get_model('lending', 'LoanPayment'),
                apps.get_model('lending', 'LoanPayment')._meta.get_field('reminder_sent'),
            ),
            lambda apps, schema_editor: None,
        ),
        migrations.RunPython(
            lambda apps, schema_editor: None if check_column_exists(
                apps, schema_editor, 'lending_loanpayment', 'reminder_sent_date'
            ) else migrations.AddField(
                model_name='loanpayment',
                name='reminder_sent_date',
                field=models.DateTimeField(blank=True, null=True),
            ).database_forwards(
                'lending', schema_editor, 
                apps.get_model('lending', 'LoanPayment'),
                apps.get_model('lending', 'LoanPayment')._meta.get_field('reminder_sent_date'),
            ),
            lambda apps, schema_editor: None,
        ),
        migrations.RunPython(
            lambda apps, schema_editor: None if check_column_exists(
                apps, schema_editor, 'lending_loanpayment', 'late_notice_sent'
            ) else migrations.AddField(
                model_name='loanpayment',
                name='late_notice_sent',
                field=models.BooleanField(default=False),
            ).database_forwards(
                'lending', schema_editor, 
                apps.get_model('lending', 'LoanPayment'),
                apps.get_model('lending', 'LoanPayment')._meta.get_field('late_notice_sent'),
            ),
            lambda apps, schema_editor: None,
        ),
        migrations.RunPython(
            lambda apps, schema_editor: None if check_column_exists(
                apps, schema_editor, 'lending_loanpayment', 'late_notice_sent_date'
            ) else migrations.AddField(
                model_name='loanpayment',
                name='late_notice_sent_date',
                field=models.DateTimeField(blank=True, null=True),
            ).database_forwards(
                'lending', schema_editor, 
                apps.get_model('lending', 'LoanPayment'),
                apps.get_model('lending', 'LoanPayment')._meta.get_field('late_notice_sent_date'),
            ),
            lambda apps, schema_editor: None,
        ),
        migrations.RunPython(
            lambda apps, schema_editor: None if check_column_exists(
                apps, schema_editor, 'lending_loanpayment', 'late_fee_amount'
            ) else migrations.AddField(
                model_name='loanpayment',
                name='late_fee_amount',
                field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12),
            ).database_forwards(
                'lending', schema_editor, 
                apps.get_model('lending', 'LoanPayment'),
                apps.get_model('lending', 'LoanPayment')._meta.get_field('late_fee_amount'),
            ),
            lambda apps, schema_editor: None,
        ),
        migrations.RunPython(
            lambda apps, schema_editor: None if check_column_exists(
                apps, schema_editor, 'lending_loanpayment', 'auto_payment_enabled'
            ) else migrations.AddField(
                model_name='loanpayment',
                name='auto_payment_enabled',
                field=models.BooleanField(default=False),
            ).database_forwards(
                'lending', schema_editor, 
                apps.get_model('lending', 'LoanPayment'),
                apps.get_model('lending', 'LoanPayment')._meta.get_field('auto_payment_enabled'),
            ),
            lambda apps, schema_editor: None,
        ),
    ]