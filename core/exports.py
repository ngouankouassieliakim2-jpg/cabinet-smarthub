import csv
from datetime import date
from django.http import HttpResponse
import openpyxl


def exporter_csv(queryset, colonnes, nom_fichier="export"):
    """colonnes : liste de tuples (en_tete, lambda obj: valeur)"""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{nom_fichier}_{date.today()}.csv"'
    writer = csv.writer(response)
    writer.writerow([c[0] for c in colonnes])
    for obj in queryset:
        writer.writerow([c[1](obj) for c in colonnes])
    return response


def exporter_excel(queryset, colonnes, nom_fichier="export"):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append([c[0] for c in colonnes])
    for obj in queryset:
        ws.append([c[1](obj) for c in colonnes])

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="{nom_fichier}_{date.today()}.xlsx"'
    wb.save(response)
    return response
