from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("reports", "0006_raast_payment_support")]

    operations = [
        migrations.AddField(
            model_name="settlementpayment",
            name="sender_raast_id",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="settlementpayment",
            name="recipient_raast_id",
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
