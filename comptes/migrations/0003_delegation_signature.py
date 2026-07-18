# Generated manually to add DelegationSignature model

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comptes', '0002_signatureelectronique_documentsigne'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DelegationSignature',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mode', models.CharField(choices=[('ORDRE', 'Par ordre'), ('DELEGATION_POUVOIR', 'Par délégation de pouvoir')], max_length=25, verbose_name='Régime')),
                ('perimetre', models.CharField(max_length=255, verbose_name='Périmètre / motif')),
                ('date_debut', models.DateField(verbose_name='Date de début')),
                ('date_fin', models.DateField(verbose_name='Date de fin')),
                ('document_preuve', models.FileField(blank=True, null=True, upload_to='delegations/preuves/', verbose_name='Document preuve')),
                ('est_active', models.BooleanField(default=True, verbose_name='Active')),
                ('date_creation', models.DateTimeField(auto_now_add=True, verbose_name='Créée le')),
                ('cree_par', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='delegations_creees', to=settings.AUTH_USER_MODEL, verbose_name='Créé par')),
                ('delegant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='delegations_donnees', to=settings.AUTH_USER_MODEL, verbose_name='Délégant')),
                ('delegataire', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='delegations_recues', to=settings.AUTH_USER_MODEL, verbose_name='Délégataire')),
            ],
            options={
                'verbose_name': 'Délégation de signature',
                'verbose_name_plural': 'Délégations de signature',
                'ordering': ['-date_creation'],
            },
        ),
    ]
