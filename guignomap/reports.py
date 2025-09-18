"""
Générateur de rapports Excel et PDF pour GuignoMap
"""

from pathlib import Path
from datetime import datetime
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
import xlsxwriter
from io import BytesIO
from guignomap.database import get_conn

# Mapping des statuts pour l'affichage (évite imports circulaires)
STATUS_TO_LABEL = {"a_faire": "À faire", "en_cours": "En cours", "terminee": "Terminée"}

# Fonctions SQLite pures pour les rapports
def extended_stats():
    with get_conn() as conn:
        cur = conn.execute("SELECT status, COUNT(*) as count FROM streets GROUP BY status")
        status_counts = dict(cur.fetchall())
        
        total = sum(status_counts.values())
        done = status_counts.get('terminee', 0)
        partial = status_counts.get('en_cours', 0) + status_counts.get('partielle', 0)
        todo = status_counts.get('a_faire', 0)
        
        return {
            'total': total,
            'done': done,
            'partial': partial,
            'todo': todo
        }

def list_streets():
    with get_conn() as conn:
        cur = conn.execute("""
            SELECT s.name, s.sector, t.nom as team, s.status, 
                   COUNT(n.id) as notes
            FROM streets s 
            LEFT JOIN teams t ON s.team_id = t.id
            LEFT JOIN notes n ON s.id = n.street_id
            GROUP BY s.id, s.name, s.sector, t.nom, s.status
            ORDER BY s.name
        """)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        return rows

def stats_by_team():
    with get_conn() as conn:
        cur = conn.execute("""
            SELECT t.nom as team_name,
                   COUNT(s.id) as total_streets,
                   SUM(CASE WHEN s.status = 'terminee' THEN 1 ELSE 0 END) as done,
                   SUM(CASE WHEN s.status IN ('en_cours', 'partielle') THEN 1 ELSE 0 END) as in_progress,
                   COUNT(n.id) as total_notes
            FROM teams t
            LEFT JOIN streets s ON t.id = s.team_id
            LEFT JOIN notes n ON s.id = n.street_id
            WHERE t.id != 'ADMIN'
            GROUP BY t.id, t.nom
            ORDER BY t.nom
        """)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

class ReportGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Définit les styles personnalisés pour PDF"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#8B0000'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#8B0000'),
            spaceAfter=12,
            spaceBefore=12
        ))
    
    def generate_excel(self):
        """Génère un rapport Excel professionnel"""
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'remove_timezone': True})
        
        # Styles Excel
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#8B0000',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
        cell_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
        status_formats = {
            'terminee': workbook.add_format({'bg_color': '#90EE90', 'border': 1}),
            'en_cours': workbook.add_format({'bg_color': '#FFE4B5', 'border': 1}),
            'a_faire': workbook.add_format({'bg_color': '#FFB6C1', 'border': 1})
        }
        
        # Feuille 1 : Résumé
        summary_sheet = workbook.add_worksheet('Résumé Guignolée 2025')
        summary_sheet.set_column(0, 4, 20)  # A:E
        
        # Titre
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 20,
            'font_color': '#8B0000',
            'align': 'center'
        })
        summary_sheet.merge_range(0, 0, 0, 4, 'GUIGNOLÉE 2025 - RELAIS DE MASCOUCHE', title_format)  # A1:E1
        summary_sheet.merge_range(1, 0, 1, 4, f'Rapport généré le {datetime.now().strftime("%d/%m/%Y à %H:%M")}', cell_format)  # A2:E2
        
        # Stats globales
        stats = extended_stats()
        
        row = 4
        summary_sheet.write(row, 0, 'STATISTIQUES GLOBALES', header_format)
        summary_sheet.merge_range(row, 1, row, 4, '', header_format)  # B{row+1}:E{row+1}
        
        row += 2
        summary_data = [
            ['Total des rues', stats['total']],
            ['Rues terminées', stats['done']],
            ['Rues en cours', stats.get('partial', 0)],
            ['Rues à faire', stats.get('todo', 0)],
            ['Progression globale', f"{(stats['done']/stats['total']*100) if stats['total'] > 0 else 0:.1f}%"],
            ['Total des notes', stats.get('total_notes', 0)],
            ['Adresses avec notes', stats.get('addresses_with_notes', 0)]
        ]
        
        for label, value in summary_data:
            summary_sheet.write(row, 0, label, cell_format)
            summary_sheet.write(row, 1, value, cell_format)
            row += 1
        
        # Feuille 2 : Détail des rues
        streets_sheet = workbook.add_worksheet('Détail des rues')
        streets_sheet.set_column(0, 0, 30)
        streets_sheet.set_column(1, 4, 15)
        
        # Headers
        headers = ['Rue', 'Secteur', 'Équipe', 'Statut', 'Notes']
        for col, header in enumerate(headers):
            streets_sheet.write(0, col, header, header_format)
        
        # Données
        street_data = list_streets()
        
        for idx, row in enumerate(street_data, 1):
            streets_sheet.write(idx, 0, row.get('name', ''), cell_format)
            streets_sheet.write(idx, 1, row.get('sector', ''), cell_format)
            streets_sheet.write(idx, 2, row.get('team', ''), cell_format)
            
            status = row.get('status', 'a_faire')
            format_to_use = status_formats.get(status, cell_format)
            status_label = STATUS_TO_LABEL.get(status, "À faire")
            streets_sheet.write(idx, 3, status_label, format_to_use)
            
            streets_sheet.write(idx, 4, row.get('notes', 0), cell_format)
        
        # Feuille 3 : Performance des équipes
        teams_sheet = workbook.add_worksheet('Performance équipes')
        teams_sheet.set_column(0, 5, 15)
        
        teams_data = stats_by_team()
        
        if teams_data:
            headers = ['Équipe', 'Total rues', 'Terminées', 'En cours', 'Notes', 'Progression %']
            for col, header in enumerate(headers):
                teams_sheet.write(0, col, header, header_format)
            
            for idx, row in enumerate(teams_data, 1):
                total = row.get('total_streets', 0)
                completed = row.get('completed', 0)
                in_progress = row.get('in_progress', 0)
                todo = row.get('todo', 0)
                progress = (completed / total * 100) if total > 0 else 0
                teams_sheet.write(idx, 0, row.get('name', ''), cell_format)
                teams_sheet.write(idx, 1, total, cell_format)
                teams_sheet.write(idx, 2, completed, cell_format)
                teams_sheet.write(idx, 3, in_progress, cell_format)
                teams_sheet.write(idx, 4, todo, cell_format)
                teams_sheet.write(idx, 5, f"{progress:.1f}%", cell_format)
        
        workbook.close()
        output.seek(0)
        return output.getvalue()
    
    def generate_pdf(self):
        """Génère un rapport PDF professionnel"""
        output = BytesIO()
        doc = SimpleDocTemplate(output, pagesize=A4)
        story = []
        
        # Page de titre
        story.append(Paragraph("GUIGNOLÉE 2025", self.styles['CustomTitle']))
        story.append(Paragraph("Le Relais de Mascouche", self.styles['Title']))
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph(f"Rapport généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}", self.styles['Normal']))
        story.append(PageBreak())
        
        # Résumé
        story.append(Paragraph("Résumé de la collecte", self.styles['SectionTitle']))
        
        # Réutilise la fonction extended_stats déjà définie ci-dessus
        stats = extended_stats()
        
        summary_data = [
            ['Statistique', 'Valeur'],
            ['Total des rues', str(stats['total'])],
            ['Rues terminées', str(stats['done'])],
            ['Rues en cours', str(stats.get('partial', 0))],
            ['Rues à faire', str(stats.get('todo', 0))],
            ['Progression', f"{(stats['done']/stats['total']*100) if stats['total'] > 0 else 0:.1f}%"],
            ['Total notes', str(stats.get('total_notes', 0))]
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8B0000')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(summary_table)
        story.append(PageBreak())
        
        # Performance des équipes
        story.append(Paragraph("Performance des équipes", self.styles['SectionTitle']))
        
        teams_data_list = stats_by_team()
        
        if teams_data_list:
            teams_data = [['Équipe', 'Total', 'Terminées', 'En cours', 'Progression']]
            for row in teams_data_list:
                total = row.get('total_streets', 0)
                completed = row.get('completed', 0)
                in_progress = row.get('in_progress', 0)
                progress = (completed / total * 100) if total > 0 else 0
                teams_data.append([
                    row.get('name', ''),
                    str(total),
                    str(completed),
                    str(in_progress),
                    f"{progress:.1f}%"
                ])
            
            teams_table = Table(teams_data, colWidths=[2*inch, 1*inch, 1*inch, 1*inch, 1.5*inch])
            teams_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8B0000')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(teams_table)
        
        doc.build(story)
        output.seek(0)
        return output.getvalue()