"""
Validateurs et sanitizers pour GuignoMap
Protection contre injections et validation des formats
"""

import re
import html
from typing import Optional, Tuple

class InputValidator:
    """Classe de validation et sanitization des entrées"""
    
    @staticmethod
    def sanitize_text(text: str, max_length: int = 255) -> str:
        """Nettoie et limite un texte"""
        if not text:
            return ""
        # Supprimer les caractères de contrôle
        text = "".join(char for char in text if ord(char) >= 32 or char == '\n')
        # Échapper le HTML
        text = html.escape(text)
        # Limiter la longueur
        return text[:max_length].strip()
    
    @staticmethod
    def sanitize_street_name(name: str) -> str:
        """Valide et nettoie un nom de rue"""
        if not name:
            return ""
        # Garder seulement lettres, chiffres, espaces, tirets, apostrophes, accents
        name = re.sub(r'[^a-zA-ZÀ-ÿ0-9\s\-\'\.]', '', name)
        return name[:100].strip()
    
    @staticmethod
    def sanitize_team_id(team_id: str) -> str:
        """Valide un ID d'équipe"""
        if not team_id:
            return ""
        # Format: LETTRES + CHIFFRES seulement, max 20 caractères
        team_id = re.sub(r'[^A-Z0-9]', '', team_id.upper())
        return team_id[:20]
    
    @staticmethod
    def sanitize_address_number(number: str) -> str:
        """Valide un numéro civique"""
        if not number:
            return ""
        # Garder chiffres et lettres (ex: 123A)
        number = re.sub(r'[^0-9A-Za-z\-]', '', number)
        return number[:10]
    
    @staticmethod
    def validate_password(password: str) -> Tuple[bool, str]:
        """Valide la force d'un mot de passe"""
        if not password:
            return False, "Mot de passe requis"
        if len(password) < 8:
            return False, "Minimum 8 caractères"
        if len(password) > 128:
            return False, "Maximum 128 caractères"
        if not re.search(r'[A-Z]', password):
            return False, "Au moins une majuscule requise"
        if not re.search(r'[a-z]', password):
            return False, "Au moins une minuscule requise"
        if not re.search(r'[0-9]', password):
            return False, "Au moins un chiffre requis"
        return True, "OK"
    
    @staticmethod
    def validate_sector(sector: str) -> str:
        """Valide un secteur"""
        valid_sectors = ['Principal', 'Centre', 'Nord', 'Sud', 'Est', 'Ouest', 'Résidentiel', '']
        if sector not in valid_sectors:
            return ''
        return sector
    
    @staticmethod
    def validate_status(status: str) -> str:
        """Valide un statut de rue"""
        valid_statuses = ['a_faire', 'en_cours', 'terminee']
        if status not in valid_statuses:
            return 'a_faire'
        return status
    
    @staticmethod
    def sanitize_note(note: str) -> str:
        """Nettoie une note/commentaire"""
        if not note:
            return ""
        # Supprimer caractères dangereux mais garder ponctuation basique
        note = re.sub(r'[<>\"\'`;]', '', note)
        return note[:500].strip()
    
    @staticmethod
    def is_sql_safe(text: str) -> bool:
        """Vérifie qu'un texte ne contient pas de patterns SQL dangereux"""
        if not text:
            return True
        dangerous_patterns = [
            r'\bDROP\b', r'\bDELETE\b', r'\bINSERT\b', r'\bUPDATE\b',
            r'\bEXEC\b', r'\bEXECUTE\b', r'--', r'/\*', r'\*/', r';'
        ]
        text_upper = text.upper()
        for pattern in dangerous_patterns:
            if re.search(pattern, text_upper):
                return False
        return True

def validate_and_clean_input(input_type: str, value: str) -> Tuple[bool, str]:
    """Fonction principale de validation"""
    validator = InputValidator()
    
    if input_type == "team_id":
        clean = validator.sanitize_team_id(value)
        return bool(clean), clean
    
    elif input_type == "street_name":
        clean = validator.sanitize_street_name(value)
        if not validator.is_sql_safe(clean):
            return False, ""
        return bool(clean), clean
    
    elif input_type == "address":
        clean = validator.sanitize_address_number(value)
        return bool(clean), clean
    
    elif input_type == "note":
        clean = validator.sanitize_note(value)
        if not validator.is_sql_safe(clean):
            return False, ""
        return bool(clean), clean
    
    elif input_type == "sector":
        clean = validator.validate_sector(value)
        return True, clean
    
    elif input_type == "status":
        clean = validator.validate_status(value)
        return True, clean
    
    elif input_type == "password":
        valid, msg = validator.validate_password(value)
        return valid, value if valid else ""
    
    else:
        clean = validator.sanitize_text(value)
        return bool(clean), clean