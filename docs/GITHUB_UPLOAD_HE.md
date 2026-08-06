<div dir="rtl">

# 🚀 העלאת המאגר ל־GitHub

## דרך הממשק

1. פתחו מאגר חדש וריק ב־GitHub.
2. חלצו את קובץ ה־ZIP במחשב.
3. העלו את **תוכן** התיקייה `KedushaVault-v1.0.0` לשורש המאגר.
4. ודאו שהקובץ `index.html` נמצא בשורש ולא בתוך תיקייה כפולה.
5. בצעו Commit בשם `Release KedushaVault 1.0.0`.

## דרך Git

```bash
git init
git add .
git commit -m "Release KedushaVault 1.0.0"
git branch -M main
git remote add origin https://github.com/USERNAME/REPOSITORY.git
git push -u origin main
```

## הפעלת האתר

1. היכנסו ל־Settings → Pages.
2. תחת Build and deployment בחרו GitHub Actions.
3. פתחו Actions והריצו את Deploy GitHub Pages.

## בדיקה לפני העלאה

```bash
python3 scripts/validate_repo.py
npm run check:js
sha256sum --check SHA256SUMS.txt
```

כל קובץ במאגר קטן ממגבלת 100MB לקובץ יחיד.

</div>
