from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import F
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from lending.models import LoanPayment, Loan
from datetime import timedelta

class Command(BaseCommand):
    help = 'Process loan payments: send reminders and handle late payments'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--no-email',
            action='store_true',
            help='Run without sending email notifications',
        )
    
    def handle(self, *args, **options):
        no_email = options.get('no_email', False)
        
        self.stdout.write(self.style.SUCCESS(f'Processing loan payments at {timezone.now()}'))
        
        # 1. Handle upcoming payments (due within 3 days)
        upcoming_payments = LoanPayment.objects.filter(
            status='pending',
            due_date__range=[timezone.now().date(), timezone.now().date() + timedelta(days=3)],
            reminder_sent=False
        )
        
        self.stdout.write(f'Found {upcoming_payments.count()} upcoming payments to remind about')
        
        for payment in upcoming_payments:
            self.send_payment_reminder(payment, no_email)
            
            # Mark reminder as sent
            payment.reminder_sent = True
            payment.reminder_sent_date = timezone.now()
            payment.save()
            
            self.stdout.write(f'Sent reminder for payment #{payment.payment_number} for loan {payment.loan.title}')
        
        # 2. Handle late payments (due date in the past)
        overdue_payments = LoanPayment.objects.filter(
            status='pending',
            due_date__lt=timezone.now().date()
        )
        
        self.stdout.write(f'Found {overdue_payments.count()} overdue payments to process')
        
        for payment in overdue_payments:
            # Mark payment as late and apply late fee
            payment.mark_as_late()
            
            # Send late notice if not already sent
            if not payment.late_notice_sent:
                self.send_late_notice(payment, no_email)
                
                # Mark late notice as sent
                payment.late_notice_sent = True
                payment.late_notice_sent_date = timezone.now()
                payment.save()
            
            self.stdout.write(f'Processed late payment #{payment.payment_number} for loan {payment.loan.title}')
        
        # 3. Process auto-payments
        auto_payments = LoanPayment.objects.filter(
            status__in=['pending', 'late'],
            due_date__lte=timezone.now().date(),
            auto_payment_enabled=True
        )
        
        self.stdout.write(f'Found {auto_payments.count()} auto-payments to process')
        
        for payment in auto_payments:
            self.process_auto_payment(payment)
            
        self.stdout.write(self.style.SUCCESS('Payment processing completed'))
    
    def send_payment_reminder(self, payment, no_email=False):
        """Send payment reminder to borrower"""
        if no_email:
            return
            
        loan = payment.loan
        borrower = loan.borrower
        
        subject = f'Payment Reminder: {loan.title} - Due in {(payment.due_date - timezone.now().date()).days} days'
        
        # Prepare email context
        context = {
            'borrower_name': f"{borrower.first_name} {borrower.last_name}",
            'loan_title': loan.title,
            'payment_number': payment.payment_number,
            'total_payments': loan.term_months,
            'amount_due': payment.amount_due,
            'due_date': payment.due_date,
            'days_until_due': (payment.due_date - timezone.now().date()).days,
            'loan_url': f"{settings.SITE_URL}/lending/loan/{loan.id}/"
        }
        
        # Render email content from template
        html_content = render_to_string('emails/payment_reminder.html', context)
        text_content = render_to_string('emails/payment_reminder.txt', context)
        
        # Send email
        try:
            send_mail(
                subject=subject,
                message=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[borrower.email],
                html_message=html_content,
                fail_silently=False
            )
            return True
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to send payment reminder: {str(e)}'))
            return False
    
    def send_late_notice(self, payment, no_email=False):
        """Send late payment notice to borrower"""
        if no_email:
            return
            
        loan = payment.loan
        borrower = loan.borrower
        
        subject = f'URGENT: Late Payment Notice for {loan.title}'
        
        # Prepare email context
        context = {
            'borrower_name': f"{borrower.first_name} {borrower.last_name}",
            'loan_title': loan.title,
            'payment_number': payment.payment_number,
            'total_payments': loan.term_months,
            'amount_due': payment.amount_due,
            'original_amount': payment.amount_due - payment.late_fee_amount,
            'late_fee': payment.late_fee_amount,
            'due_date': payment.due_date,
            'days_overdue': payment.days_overdue(),
            'loan_url': f"{settings.SITE_URL}/lending/loan/{loan.id}/"
        }
        
        # Render email content from template
        html_content = render_to_string('emails/late_payment_notice.html', context)
        text_content = render_to_string('emails/late_payment_notice.txt', context)
        
        # Send email
        try:
            send_mail(
                subject=subject,
                message=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[borrower.email],
                html_message=html_content,
                fail_silently=False
            )
            return True
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to send late payment notice: {str(e)}'))
            return False
    
    def process_auto_payment(self, payment):
        """Process automatic payment for eligible payments"""
        loan = payment.loan
        borrower = loan.borrower
        
        # Check if borrower has sufficient funds
        try:
            wallet = borrower.wallet
            if wallet.balance >= payment.amount_due:
                # Process the payment
                from lending.models import process_loan_repayment
                result = process_loan_repayment(loan, payment.amount_due)
                
                if result['success']:
                    self.stdout.write(self.style.SUCCESS(
                        f'Auto-payment processed successfully for payment #{payment.payment_number} of loan {loan.title}'
                    ))
                else:
                    self.stdout.write(self.style.ERROR(
                        f'Auto-payment failed for payment #{payment.payment_number}: {result["message"]}'
                    ))
            else:
                self.stdout.write(self.style.WARNING(
                    f'Insufficient funds for auto-payment #{payment.payment_number} of loan {loan.title}'
                ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error processing auto-payment: {str(e)}'))