"""
Tests pour le module guignomap.imports
"""
import pytest
import pandas as pd
from guignomap.imports import normalize_text, build_addr_key, detect_schema, prepare_dataframe


class TestNormalizeText:
    """Tests pour la fonction normalize_text"""
    
    def test_normalize_text_no_nan_emission(self):
        """Vérifie que normalize_text n'émet jamais 'nan'"""
        test_cases = [
            None,
            "nan",
            "NaN", 
            "NAN",
            "",
            "   ",
            pd.NA,
            float('nan'),
            "Rue Saint-Émile",
            "Avenue de l'École",
            "123",
            "Montée du Château",
            "Boulevard René-Lévesque"
        ]
        
        for test_case in test_cases:
            result = normalize_text(test_case)
            assert isinstance(result, str), f"Result should be string for input: {test_case}"
            assert result != "nan", f"normalize_text should never return 'nan' for input: {test_case}"
            assert result.lower() != "nan", f"normalize_text should never return 'nan' (case insensitive) for input: {test_case}"
    
    def test_normalize_text_handles_accents(self):
        """Vérifie la gestion des accents"""
        test_cases = [
            ("Émile", "Emile"),
            ("François", "Francois"), 
            ("Montréal", "Montreal"),
            ("Québec", "Quebec"),
            ("Côte-des-Neiges", "Cote-des-Neiges")
        ]
        
        for input_text, expected in test_cases:
            result = normalize_text(input_text)
            assert result == expected, f"Expected '{expected}', got '{result}'"
    
    def test_normalize_text_handles_apostrophes(self):
        """Vérifie la gestion des apostrophes"""
        test_cases = [
            ("l'École", "l Ecole"),
            ("d'Artagnan", "d Artagnan"),
            ("Saint-Jean-l'Évangéliste", "Saint-Jean-l Evangeliste")
        ]
        
        for input_text, expected in test_cases:
            result = normalize_text(input_text)
            assert result == expected, f"Expected '{expected}', got '{result}'"


class TestBuildAddrKey:
    """Tests pour la fonction build_addr_key"""
    
    def test_build_addr_key_stability_accents(self):
        """Vérifie la stabilité sur les accents"""
        test_cases = [
            ("Rue Émile", "123", None),
            ("Avenue François", "456", "H1A 1A1"),
            ("Montée du Château", "789", "")
        ]
        
        for street, number, postal in test_cases:
            # Générer la clé deux fois
            key1 = build_addr_key(street, number, postal)
            key2 = build_addr_key(street, number, postal)
            
            assert key1 == key2, f"build_addr_key should be stable: {key1} != {key2}"
            assert isinstance(key1, str), "build_addr_key should return string"
            assert "|" in key1, "build_addr_key should contain separator"
    
    def test_build_addr_key_stability_apostrophes(self):
        """Vérifie la stabilité sur les apostrophes"""
        test_cases = [
            ("Rue de l'École", "123"),
            ("Avenue d'Artagnan", "456"), 
            ("Place de l'Hôtel-de-Ville", "789")
        ]
        
        for street, number in test_cases:
            key1 = build_addr_key(street, number)
            key2 = build_addr_key(street, number)
            
            assert key1 == key2, f"build_addr_key should be stable with apostrophes: {key1} != {key2}"
            # Vérifier que la clé ne contient pas d'apostrophes (remplacées par des espaces)
            assert "'" not in key1 and "'" not in key1, f"Key should have normalized apostrophes: {key1}"
    
    def test_build_addr_key_format(self):
        """Vérifie le format de la clé générée"""
        key = build_addr_key("Rue Test", "123", "H1A 1A1")
        parts = key.split("|")
        
        assert len(parts) == 3, f"Key should have 3 parts separated by |: {key}"
        assert parts[0] != "", "Street part should not be empty"
        assert parts[1] != "", "Number part should not be empty"
        # parts[2] peut être vide si pas de code postal
    
    def test_build_addr_key_no_postal(self):
        """Vérifie le format sans code postal"""
        key = build_addr_key("Rue Test", "123", None)
        assert key.endswith("|"), f"Key without postal should end with |: {key}"
        
        key2 = build_addr_key("Rue Test", "123", "")
        assert key2.endswith("|"), f"Key with empty postal should end with |: {key2}"


class TestDetectSchema:
    """Tests pour la fonction detect_schema"""
    
    def test_detect_schema_mascouche_format(self):
        """Teste la détection du format Mascouche"""
        df = pd.DataFrame({
            'NoCiv': [123, 456],
            'nomrue': ['Rue Test', 'Avenue Example'],
            'OdoGener': ['', ''],
            'OdoParti': ['', 'des'],
            'OdoSpeci': ['Test', 'Examples']
        })
        
        mapping = detect_schema(df, 'mascouche')
        
        assert 'street' in mapping, "Should detect street column"
        assert 'number' in mapping, "Should detect number column"
        assert mapping['street'] == 'nomrue', f"Should map street to 'nomrue', got {mapping['street']}"
        assert mapping['number'] == 'NoCiv', f"Should map number to 'NoCiv', got {mapping['number']}"
    
    def test_detect_schema_generic_format(self):
        """Teste la détection sur un format générique"""
        df = pd.DataFrame({
            'Street_Name': ['Main St', 'Oak Ave'],
            'House_Number': [123, 456],
            'Postal_Code': ['A1A 1A1', 'B2B 2B2']
        })
        
        mapping = detect_schema(df, 'test')
        
        assert 'street' in mapping, "Should detect street column"
        assert 'number' in mapping, "Should detect number column"


class TestPrepareDataframe:
    """Tests pour la fonction prepare_dataframe"""
    
    def test_prepare_dataframe_basic(self):
        """Test de base de prepare_dataframe"""
        df = pd.DataFrame({
            'nomrue': ['Rue Test', 'Avenue Example', ''],
            'NoCiv': [123, 456, 789],
            'autre': ['data', 'more', 'stuff']
        })
        
        mapping = {'street': 'nomrue', 'number': 'NoCiv'}
        result = prepare_dataframe(df, mapping, 'test')
        
        assert len(result) == 2, "Should filter out empty streets"  # ligne vide exclue
        assert 'street_name' in result.columns, "Should have street_name column"
        assert 'house_number' in result.columns, "Should have house_number column"
        assert 'addr_key' in result.columns, "Should have addr_key column"
        
        # Vérifier que les clés sont uniques
        assert len(result['addr_key'].unique()) == len(result), "All addr_keys should be unique"
    
    def test_prepare_dataframe_missing_mapping(self):
        """Test avec mapping incomplet"""
        df = pd.DataFrame({'col1': [1, 2], 'col2': ['a', 'b']})
        mapping = {'street': 'col1'}  # Manque 'number'
        
        with pytest.raises(ValueError, match="Mapping doit contenir au minimum"):
            prepare_dataframe(df, mapping, 'test')