from django.db import migrations, models


def convert_payments(apps, schema_editor):
    Payment = apps.get_model("tracker", "Payment")
    # Unmatched SMS payments have no member and cannot be kept.
    Payment.objects.filter(member__isnull=True).delete()
    Payment.objects.filter(status="recorded").update(status="success")
    Payment.objects.filter(status__in=["review", "unassigned"]).update(status="failed")
    Payment.objects.filter(source="sms").update(source="manual")


class Migration(migrations.Migration):
    dependencies = [("tracker", "0001_initial")]

    operations = [
        migrations.DeleteModel(name="IncomingMessage"),
        migrations.DeleteModel(name="NotificationLog"),
        migrations.DeleteModel(name="PayerAlias"),
        migrations.RemoveField(model_name="payment", name="suggested_member"),
        migrations.RemoveField(model_name="payment", name="payer_name"),
        migrations.RemoveField(model_name="payment", name="payer_phone"),
        migrations.RemoveField(model_name="payment", name="account_text"),
        migrations.RemoveField(model_name="payment", name="raw_message"),
        migrations.RemoveField(model_name="member", name="mpesa_phone"),
        migrations.RenameField(model_name="payment", old_name="mpesa_code", new_name="reference"),
        migrations.RunPython(convert_payments, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="payment",
            name="reference",
            field=models.CharField(max_length=40, unique=True),
        ),
        migrations.AlterField(
            model_name="payment",
            name="member",
            field=models.ForeignKey(on_delete=models.PROTECT, related_name="payments", to="tracker.member"),
        ),
        migrations.AlterField(
            model_name="payment",
            name="status",
            field=models.CharField(
                choices=[("pending", "Pending"), ("success", "Paid"), ("failed", "Failed"), ("reversed", "Reversed")],
                default="pending",
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name="payment",
            name="source",
            field=models.CharField(
                choices=[("paystack", "Paystack"), ("manual", "Entered by treasurer")], default="paystack", max_length=8
            ),
        ),
        migrations.AlterField(model_name="payment", name="paid_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(
            model_name="payment",
            name="channel",
            field=models.CharField(blank=True, help_text="Paystack channel, e.g. mobile_money, card", max_length=30),
        ),
        migrations.AlterField(model_name="member", name="email", field=models.EmailField(max_length=254)),
        migrations.AlterModelOptions(name="payment", options={"ordering": ["-created_at", "-id"]}),
    ]
