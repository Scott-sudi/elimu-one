# Exploitation de production

## Architecture

- Apache et Passenger o2switch executent `backend/passenger_wsgi.py`.
- Django utilise `config.settings.production`.
- WhiteNoise sert les fichiers statiques produits par `collectstatic`.
- MySQL est accessible uniquement par Django avec les variables `DB_*`.
- Les medias restent sur le disque o2switch et sont inclus dans les backups.
- L'API publique est versionnee sous `/api/v1/` et utilise JWT access/refresh.

## Securite appliquee

- `DEBUG=False`, hotes et origines CSRF explicites.
- Redirection HTTPS, cookies de session et CSRF securises.
- HSTS, `X-Frame-Options=DENY`, protection XSS, no-sniff et politique de referent.
- Mots de passe haches, verrouillage des tentatives de connexion et audit.
- JWT avec rotation et liste noire de refresh tokens a la deconnexion.
- JSON uniquement pour l'API en production; l'interface API browsable est desactivee.

## Routine apres chaque mise a jour

```sh
cd ~/kalunga-school/backend
source /home/CPANELUSER/virtualenv/kalunga-school/3.11/bin/activate
./scripts/deploy.sh
python manage.py check --deploy
```

Le chemin de l'environnement virtuel est celui affiche par cPanel. Ne le devinez pas.

## Logs

Les logs sont dans `backend/logs/` ou dans `DJANGO_LOG_DIR` :

- `django.log`: activite Django generale.
- `error.log`: exceptions et erreurs.
- `security.log`: avertissements de securite Django.

Consultez-les dans cPanel File Manager ou Terminal. Ils ne sont pas versionnes.