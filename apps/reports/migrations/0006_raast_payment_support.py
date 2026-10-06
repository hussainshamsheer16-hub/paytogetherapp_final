from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("reports", "0005_alter_settlementpayment_status_notification")]

    operations = [
        migrations.AlterField(
            model_name="settlementpayment",
            name="payment_method",
            field=models.CharField(
                choices=[("cod", "Cash on delivery"), ("card", "Bank card"), ("raast", "Raast")],
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name="settlementpayment",
            name="status",
            field=models.CharField(
                choices=[
                    ("unpaid", "Unpaid"), ("pending", "Pending approval"),
                    ("paid", "Paid"), ("received", "Received"),
                    ("not_received", "Not received"), ("failed", "Failed"),
                    ("cancelled", "Cancelled"), ("processing", "Processing"),
                    ("expired", "Expired"),
                ],
                default="unpaid",
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name="settlementpayment",
            name="provider_reference",
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),
        migrations.AddConstraint(
            model_name="settlementpayment",
            constraint=models.UniqueConstraint(
                fields=("tour", "payer", "recipient", "amount"),
                name="unique_tour_settlement_payment",
            ),
        ),
    ]
