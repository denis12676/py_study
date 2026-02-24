"""
Skript proverki bezopasnosti pered deploy
Proveryaet chto API klyuch ne popadet v Git
"""

import os
import sys

def check_security():
    """Proverka bezopasnosti pered deploy v Streamlit Cloud"""
    print("Proverka bezopasnosti pered deploy v Streamlit Cloud")
    print("="*60)
    
    issues = []
    warnings = []
    
    # 1. Proverka .gitignore
    print("\n1. Proverka .gitignore...")
    if os.path.exists('.gitignore'):
        with open('.gitignore', 'r') as f:
            content = f.read()
            
        if '.env' in content:
            print("   [OK] .env fajly isklyucheny iz Git")
        else:
            issues.append("[ERROR] .env NE isklyuchen iz Git!")
            
        if 'secrets.toml' in content:
            print("   [OK] secrets.toml isklyuchen iz Git")
        else:
            issues.append("[ERROR] secrets.toml NE isklyuchen iz Git!")
    else:
        issues.append("[ERROR] Fajl .gitignore otsutstvuet!")
    
    # 2. Proverka na nalichie .env
    print("\n2. Proverka .env fajla...")
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            content = f.read()
            if 'WB_API_TOKEN' in content and len(content.strip()) > 50:
                warnings.append("[WARN] .env fajl sushchestvuet i soderzhit token")
                print("   [WARN] .env fajl najden (ubedites chto on v .gitignore)")
            else:
                print("   [OK] .env fajl ne soderzhit token ili pust")
    else:
        print("   [INFO] .env fajl ne najden (normalno dlya deploy)")
    
    # 3. Proverka secrets.toml
    print("\n3. Proverka secrets.toml...")
    if os.path.exists('.streamlit/secrets.toml'):
        with open('.streamlit/secrets.toml', 'r') as f:
            content = f.read()
            if 'your_api_token' not in content and 'WB_API_TOKEN' in content:
                issues.append("[ERROR] .streamlit/secrets.toml soderzhit REALNYJ token!")
                print("   [ERROR] Fajl soderzhit realnyj token!")
            else:
                print("   [OK] secrets.toml soderzhit tolko shablon")
    else:
        print("   [INFO] secrets.toml ne najden (normalno, budet v oblake)")
    
    # 4. Proverka koda na zhestko zakodirovannye tokeny
    print("\n4. Proverka koda na tokeny...")
    sensitive_files = ['dashboard.py', 'ai_agent.py', 'wb_client.py']
    found_tokens = []
    
    for file in sensitive_files:
        if os.path.exists(file):
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'eyJhbGci' in content or 'eyJ0eXAiOi' in content:
                    found_tokens.append(file)
    
    if found_tokens:
        issues.append(f"[ERROR] Najdeny tokeny v fajlah: {', '.join(found_tokens)}")
    else:
        print("   [OK] Zhestko zakodirovannye tokeny ne najdeny")
    
    # 5. Proverka imports v dashboard.py
    print("\n5. Proverka podderzhki Streamlit Secrets...")
    if os.path.exists('dashboard.py'):
        with open('dashboard.py', 'r', encoding='utf-8') as f:
            content = f.read()
            if 'st.secrets' in content:
                print("   [OK] Podderzhka Streamlit Secrets najdena")
            else:
                warnings.append("[WARN] Podderzhka Streamlit Secrets ne najdena")
    
    # Itogi
    print("\n" + "="*60)
    print("REZULTAT PROVERKI:")
    print("="*60)
    
    if issues:
        print("\n[ERROR] KRITICHESKIE OSIBKI:")
        for issue in issues:
            print(f"   {issue}")
        print("\n[BLOCK] DEPLOY ZAPRESHCHEN!")
        print("Ispravte oshibki pered deploy.")
        return False
    
    if warnings:
        print("\n[WARN] PREDUPREZHDENIYA:")
        for warning in warnings:
            print(f"   {warning}")
        print("\n[OK] Mozhno deployit, no proverte preduprezhdeniya")
    else:
        print("\n[OK] VSE PROVERKI PROJDENY!")
        print("Mozhno bezopasno deployit v Streamlit Cloud.")
    
    print("\n" + "="*60)
    print("Sleduyushchie shagi:")
    print("1. Otpravte kod v GitHub (git push)")
    print("2. Zajdite v https://streamlit.io/cloud")
    print("3. Sozdaite novoe prilozhenie iz repozitoriya")
    print("4. Dobavte WB_API_TOKEN v Settings → Secrets")
    print("="*60)
    
    return len(issues) == 0

if __name__ == "__main__":
    if check_security():
        sys.exit(0)
    else:
        sys.exit(1)
