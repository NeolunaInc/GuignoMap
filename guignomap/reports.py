# reports.py — stub minimal pour robustesse
# Ce module est optionnel et peut être remplacé par une vraie implémentation.

"""Module de rapports - stub minimal pour compatibilité"""

class ReportGenerator:
    def __init__(self, conn):
        self.conn = conn
    
    def generate_pdf(self):
        return b"PDF non disponible"
    
    def generate_excel(self):
        import pandas as pd
        from io import BytesIO
        output = BytesIO()
        df = pd.DataFrame({"Message": ["Utilisez l'export depuis l'interface gestionnaire"]})
        df.to_excel(output, index=False)
        return output.getvalue()

REPORTS_AVAILABLE = True
