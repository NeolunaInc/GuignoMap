import os
import sys
import socket
import psycopg2
import pytest

RUN_DB_EXT = bool(os.getenv("RUN_DB_EXT_TESTS"))

@pytest.mark.skipif(not RUN_DB_EXT, reason="External DB tests disabled; set RUN_DB_EXT_TESTS=1 to run")
def test_connection_with_ip():
    """Test connection with direct IPv6 address"""
    # Configuration manuelle avec l'adresse IPv6 résolue
    ipv6_host = "2600:1f11:4e2:e202:6514:7431:494f:c00f"
    
    connection_string = f"postgresql://postgres:4everSab!2304@[{ipv6_host}]:5432/postgres"
    
    print(f"Test de connexion avec IPv6 directe: {ipv6_host}")
    
    try:
        conn = psycopg2.connect(connection_string)
        print("✅ Connexion IPv6 réussie!")
        
        with conn.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f"Version PostgreSQL: {version}")
        
        conn.close()
        assert True  # Connection successful
        
    except Exception as e:
        print(f"❌ Erreur de connexion IPv6: {e}")
        assert False, f"IPv6 connection failed: {e}"

@pytest.mark.skipif(not RUN_DB_EXT, reason="External DB tests disabled; set RUN_DB_EXT_TESTS=1 to run")
def test_connection_with_hostname():
    """Test connection with hostname via custom DNS"""
    import socket
    
    # Forcer IPv4 si possible
    try:
        socket.setdefaulttimeout(10)
        original_getaddrinfo = socket.getaddrinfo
        
        def custom_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
            if host == "db.kdxqspmfycnwzzrmhzpa.supabase.co":
                # Retourner directement l'IPv6 connue
                return [(socket.AF_INET6, socket.SOCK_STREAM, 6, '', 
                        ('2600:1f11:4e2:e202:6514:7431:494f:c00f', port, 0, 0))]
            return original_getaddrinfo(host, port, family, type, proto, flags)
        
        socket.getaddrinfo = custom_getaddrinfo
        
        connection_string = "postgresql://postgres:4everSab!2304@db.kdxqspmfycnwzzrmhzpa.supabase.co:5432/postgres"
        
        print("Test de connexion avec hostname (DNS custom)")
        conn = psycopg2.connect(connection_string)
        print("✅ Connexion hostname réussie!")
        
        with conn.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f"Version PostgreSQL: {version}")
        
        conn.close()
        socket.getaddrinfo = original_getaddrinfo
        assert True  # Connection successful
        
    except Exception as e:
        print(f"❌ Erreur de connexion hostname: {e}")
        socket.getaddrinfo = original_getaddrinfo
        assert False, f"Hostname connection failed: {e}"

if __name__ == "__main__":
    print("=== Test de connectivité Supabase PostgreSQL ===")
    
    print("\n1. Test avec adresse IPv6 directe:")
    try:
        test_connection_with_ip()
        ipv6_success = True
    except AssertionError:
        ipv6_success = False
    
    print("\n2. Test avec hostname (DNS custom):")
    try:
        test_connection_with_hostname()
        hostname_success = True
    except AssertionError:
        hostname_success = False
    
    if ipv6_success or hostname_success:
        print("\n✅ Au moins une méthode de connexion fonctionne!")
    else:
        print("\n❌ Aucune méthode de connexion ne fonctionne")
        print("Problème potentiel: connectivité IPv6 ou firewall")