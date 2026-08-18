# Deploiement o2switch pour institut-kalunga.net

Ce guide utilise cPanel, Apache et Passenger d'o2switch. Il ne requiert ni Docker,
ni Nginx personnalise, ni service cloud externe.

Domaine de production : **https://institut-kalunga.net**

## 0. DNS (obligatoire avant tout le reste)

Le domaine doit resolvable publiquement. Si `nslookup institut-kalunga.net`
renvoie *Non-existent domain*, le site ne pourra pas s'ouvrir.

Dans cPanel :

1. **Domaines** : confirmez que `institut-kalunga.net` est bien liste.
2. **Zone Editor** (ou DNS) : verifiez un enregistrement **A** (et eventuellement
   **www** en CNAME ou A) pointant vers l'IP du serveur o2switch.
3. Chez le **registrar** (ou revendeur o2switch) : les nameservers doivent etre
   ceux indiques par o2switch (souvent `*.o2switch.net`).
4. Attendez la propagation DNS (quelques minutes a 24 h), puis testez :

```sh
nslookup institut-kalunga.net
```

Ne passez aux etapes suivantes que lorsque le nom resout vers une adresse IP.

## 1. Creer MySQL dans cPanel

1. Ouvrez cPanel puis **MySQL Databases**.
2. Creez la base `kalunga`.
3. Creez un utilisateur MySQL avec un mot de passe long genere par cPanel.
4. Ajoutez cet utilisateur a la base et cochez **ALL PRIVILEGES**.
5. Notez les noms complets affiches par cPanel. Ils contiennent souvent le prefixe du compte, par exemple `cpuser_kalunga`.

## 2. Installer le code

1. Ouvrez **Terminal** dans cPanel.
2. Placez le depot hors de `public_html` :

```sh
cd ~
git clone URL_DU_DEPOT_GIT kalunga-school
cd ~/kalunga-school
```

3. Ne televersez pas `.env`, `media`, `logs`, `staticfiles`, `node_modules` ou `.venv` depuis votre ordinateur.
4. Si le depot est prive, utilisez une cle SSH de deploiement ou **Git Version Control** dans cPanel. Ne mettez jamais un mot de passe Git dans une commande.

## 3. Creer l'application Python

1. Dans cPanel, ouvrez **Setup Python App** ou **Select Python Version**.
2. Cliquez sur **Create Application**.
3. Choisissez Python 3.10 ou plus recent, de preference la version la plus recente proposee par o2switch.
4. Choisissez le domaine `institut-kalunga.net`, puis l'URL `/`.
5. Definissez **Application root** sur `kalunga-school/backend`.
6. Creez l'application et copiez exactement le chemin de l'environnement virtuel affiche par cPanel.
7. Verifiez que le fichier de demarrage est `passenger_wsgi.py`. Le depot contient deja `backend/passenger_wsgi.py`.

## 4. Installer les dependances et compiler les assets

Dans le terminal cPanel, adaptez uniquement le chemin d'activation avec celui affiche
par cPanel :

```sh
cd ~/kalunga-school
source /home/CPANELUSER/virtualenv/kalunga-school/3.11/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt
npm ci
npm run build
```

Si npm n'est pas disponible sur votre formule, lancez `npm ci` et `npm run build` sur
votre ordinateur, puis envoyez uniquement le repertoire `backend/static/dist/` genere.

## 5. Creer le fichier .env de production

1. Dans cPanel File Manager, ouvrez le dossier `kalunga-school`.
2. Creez le fichier cache `.env` au meme niveau que `backend`.
3. Copiez le bloc **Production minimale** de [ENVIRONMENT.md](ENVIRONMENT.md).
4. Remplacez `CPANELUSER`, les noms MySQL, les mots de passe et les chemins absolus.
5. Generez `DJANGO_SECRET_KEY` dans le terminal :

```sh
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

6. Gardez `DJANGO_DEBUG=False`, `DJANGO_SECURE_SSL_REDIRECT=True` et les domaines
   `institut-kalunga.net,www.institut-kalunga.net`.

## 6. Initialiser Django

```sh
cd ~/kalunga-school/backend
source /home/CPANELUSER/virtualenv/kalunga-school/3.11/bin/activate
python manage.py migrate --noinput
python manage.py initialize_roles
python manage.py collectstatic --noinput
python manage.py check --deploy
```

Le premier administrateur est cree une seule fois via `https://institut-kalunga.net/setup/`.
Ne creez pas de compte administrateur partage.

## 7. Rendre les medias disponibles

WhiteNoise sert les fichiers statiques depuis `STATIC_ROOT`. Pour les medias, creez un
lien symbolique Apache dans le repertoire web du domaine. Remplacez `public_html` par
le vrai document root indique dans cPanel si votre domaine en utilise un autre :

```sh
ln -s ~/kalunga-school/backend/media ~/public_html/media
```

Testez ensuite une URL de photo eleve. Si o2switch refuse le lien symbolique, ouvrez un
ticket avec ce texte precis : "Merci d'autoriser le service Apache du dossier
/home/CPANELUSER/kalunga-school/backend/media sur institut-kalunga.net/media/."

## 8. HTTPS et demarrage

1. Dans cPanel, ouvrez **SSL/TLS Status** et lancez **Run AutoSSL** pour
   `institut-kalunga.net` et `www.institut-kalunga.net`.
2. Attendez que les deux certificats soient valides.
3. Dans **Setup Python App**, cliquez sur **Restart**. Sinon lancez `touch ~/kalunga-school/backend/tmp/restart.txt`.
4. Ouvrez `https://institut-kalunga.net/api/v1/health/`, puis `https://institut-kalunga.net/`.
5. Testez une connexion, un upload de photo et une deconnexion API.

Ne mettez `DJANGO_SECURE_SSL_REDIRECT=False` que temporairement si le certificat n'est
pas encore actif. Remettez immediatement `True`, puis redemarrez Passenger.
