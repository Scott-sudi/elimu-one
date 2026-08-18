# Sauvegarde et restauration

Une sauvegarde complete contient toujours MySQL et le repertoire media. La base seule
ne contient pas les photos, QR codes, documents, rapports PDF ni recus.

## Creer une sauvegarde sur o2switch

Dans le terminal cPanel, apres activation de l'environnement Python :

```sh
cd ~/kalunga-school/backend
./scripts/backup_database.sh ~/backups/kalunga
```

Le script cree un fichier `.sql` et un fichier `media-*.tar.gz`. Telechargez les deux
fichiers hors du serveur. Conservez une copie quotidienne sur 30 jours et une copie
mensuelle hors site.

## Restaurer

1. Redirigez temporairement le domaine vers une page de maintenance depuis cPanel.
2. Televersez les deux fichiers de sauvegarde sur le serveur.
3. Lancez la commande suivante :

```sh
cd ~/kalunga-school/backend
./scripts/restore_database.sh /home/CPANELUSER/backups/kalunga/DB.sql /home/CPANELUSER/backups/kalunga/MEDIA.tar.gz
```

4. Tapez exactement `RESTORE` lorsque le script le demande.
5. Lancez `./scripts/deploy.sh`, puis testez la connexion et une photo eleve.

La restauration remplace la base cible. Testez d'abord la procedure sur une base de
recette si elle est disponible.