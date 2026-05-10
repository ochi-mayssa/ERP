import random
from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from inventory.models import Product, BomItem, Transaction
from crm.models import Lead, Customer, Opportunity, Quotation, QuotationLine, SalesOrder, SalesOrderLine, Invoice, Payment

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds the database with demo ERP and CRM data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding demo data...')

        # 1. Ensure we have a user
        user, _ = User.objects.get_or_create(username='admin', defaults={'is_staff': True, 'is_superuser': True})
        if _:
            user.set_password('admin123')
            user.save()

        # 2. Create Products
        # Raw Materials
        steel_sheet, _ = Product.objects.get_or_create(
            sku='RM-STL-001',
            defaults={
                'name': 'Steel Sheet 2mm',
                'unit': 'm2',
                'stock_quantity': 500,
                'reorder_level': 100,
                'is_raw_material': True,
                'average_cost': Decimal('15.50')
            }
        )
        plastic_pellets, _ = Product.objects.get_or_create(
            sku='RM-PLT-001',
            defaults={
                'name': 'Plastic Pellets (ABS)',
                'unit': 'kg',
                'stock_quantity': 1000,
                'reorder_level': 200,
                'is_raw_material': True,
                'average_cost': Decimal('2.75')
            }
        )
        motor, _ = Product.objects.get_or_create(
            sku='RM-MTR-001',
            defaults={
                'name': 'Electric Motor 12V',
                'unit': 'pcs',
                'stock_quantity': 50,
                'reorder_level': 10,
                'is_raw_material': True,
                'average_cost': Decimal('45.00')
            }
        )

        # Finished Goods
        industrial_fan, _ = Product.objects.get_or_create(
            sku='FG-FAN-001',
            defaults={
                'name': 'Industrial Cooling Fan',
                'unit': 'pcs',
                'stock_quantity': 25,
                'reorder_level': 5,
                'is_raw_material': False,
                'selling_price': Decimal('250.00'),
                'labor_hours_per_unit': Decimal('2.5'),
                'labor_hourly_rate': Decimal('20.00')
            }
        )
        storage_bin, _ = Product.objects.get_or_create(
            sku='FG-BIN-001',
            defaults={
                'name': 'Heavy Duty Storage Bin',
                'unit': 'pcs',
                'stock_quantity': 100,
                'reorder_level': 20,
                'is_raw_material': False,
                'selling_price': Decimal('45.00'),
                'labor_hours_per_unit': Decimal('0.5'),
                'labor_hourly_rate': Decimal('15.00')
            }
        )

        # 3. Create BOMs
        BomItem.objects.get_or_create(finished_product=industrial_fan, raw_material=steel_sheet, defaults={'quantity_needed': Decimal('1.5')})
        BomItem.objects.get_or_create(finished_product=industrial_fan, raw_material=motor, defaults={'quantity_needed': Decimal('1.0')})
        BomItem.objects.get_or_create(finished_product=storage_bin, raw_material=plastic_pellets, defaults={'quantity_needed': Decimal('0.8')})

        # 4. Create Leads
        leads_data = [
            {'company_name': 'Global Tech Solutions', 'contact_person': 'John Smith', 'email': 'john@globaltech.com', 'phone': '555-0101', 'source': 'website', 'status': 'new', 'estimated_value': 5000},
            {'company_name': 'Industrial Dynamics', 'contact_person': 'Sarah Brown', 'email': 'sarah@ind-dyn.com', 'phone': '555-0102', 'source': 'referral', 'status': 'contacted', 'estimated_value': 12000},
            {'company_name': 'Eco Manufacturing', 'contact_person': 'Mike Wilson', 'email': 'mike@ecoman.com', 'phone': '555-0103', 'source': 'trade_show', 'status': 'qualified', 'estimated_value': 8500},
        ]
        for data in leads_data:
            Lead.objects.get_or_create(company_name=data['company_name'], defaults={**data, 'assigned_to': user})

        # 5. Create Customers
        customers_data = [
            {'company_name': 'Build-It Corp', 'contact_person': 'Alice Cooper', 'email': 'alice@buildit.com', 'phone': '555-0201', 'credit_limit': 50000, 'payment_terms': 'Net 30'},
            {'company_name': 'Mega Logistics', 'contact_person': 'Bob Marley', 'email': 'bob@megalog.com', 'phone': '555-0202', 'credit_limit': 100000, 'payment_terms': 'Net 60'},
        ]
        customers = []
        for data in customers_data:
            cust, _ = Customer.objects.get_or_create(company_name=data['company_name'], defaults={**data, 'assigned_to': user})
            customers.append(cust)

        # 6. Create Opportunities
        opp1 = Opportunity.objects.create(
            customer=customers[0],
            product=industrial_fan,
            quantity=20,
            unit_price=Decimal('240.00'),
            probability=70,
            expected_close_date=timezone.now().date() + timedelta(days=15),
            stage='negotiation',
            created_by=user
        )

        opp2 = Opportunity.objects.create(
            customer=customers[1],
            product=storage_bin,
            quantity=200,
            unit_price=Decimal('40.00'),
            probability=90,
            expected_close_date=timezone.now().date() + timedelta(days=5),
            stage='proposal_sent',
            created_by=user
        )

        # 7. Create Quotations
        quote = Quotation.objects.create(
            customer=customers[0],
            opportunity=opp1,
            valid_until=timezone.now().date() + timedelta(days=30),
            status='sent',
            created_by=user
        )
        QuotationLine.objects.create(quotation=quote, product=industrial_fan, quantity=20, unit_price=Decimal('240.00'))

        # 8. Create Sales Orders
        so = SalesOrder.objects.create(
            customer=customers[1],
            order_date=timezone.now().date() - timedelta(days=2),
            delivery_date=timezone.now().date() + timedelta(days=7),
            status='confirmed',
            total_amount=Decimal('8000.00')
        )
        SalesOrderLine.objects.create(sales_order=so, product=storage_bin, quantity_ordered=200, unit_price=Decimal('40.00'))

        # 9. Create Invoices and Payments
        inv = Invoice.objects.create(
            sales_order=so,
            customer=customers[1],
            invoice_date=timezone.now().date() - timedelta(days=1),
            due_date=timezone.now().date() + timedelta(days=29),
            total_amount=Decimal('8000.00'),
            status='sent'
        )

        Payment.objects.create(
            invoice=inv,
            amount=Decimal('2000.00'),
            payment_date=timezone.now().date(),
            method='bank_transfer',
            recorded_by=user
        )
        inv.amount_paid = Decimal('2000.00')
        inv.save()

        # Update customer credit used
        customers[1].credit_used = Decimal('2000.00')
        customers[1].save()

        self.stdout.write(self.style.SUCCESS('Successfully seeded demo data'))
