import 'app_language.dart';

/// Chaînes UI parents — Français / English / Kiswahili (sans codegen).
class AppStrings {
  const AppStrings._(this.lang);

  final AppLanguage lang;

  factory AppStrings.of(AppLanguage language) => AppStrings._(language);

  String _t(String fr, String en, String sw) => switch (lang) {
        AppLanguage.fr => fr,
        AppLanguage.en => en,
        AppLanguage.sw => sw,
      };

  // —— Navigation ——
  String get navHome => _t('Accueil', 'Home', 'Nyumbani');
  String get navChildren => _t('Mes Enfants', 'My Children', 'Watoto wangu');
  String get navNotifications =>
      _t('Notifications', 'Notifications', 'Arifa');
  String get navAbout => _t('À propos', 'About', 'Kuhusu');
  String get navAccount => _t('Mon Compte', 'My Account', 'Akaunti yangu');

  // —— Compte ——
  String get accountTitle => navAccount;
  String get parentTutor =>
      _t('Parent / Tuteur', 'Parent / Guardian', 'Mzazi / Mlezi');
  String get accountSettings =>
      _t('Paramètres du compte', 'Account settings', 'Mipangilio ya akaunti');
  String get personalInfo => _t(
        'Informations personnelles',
        'Personal information',
        'Taarifa binafsi',
      );
  String get languageMenu => _t('Langue', 'Language', 'Lugha');
  String get theme => _t('Thème', 'Theme', 'Mandhari');
  String get themeLight => _t('Clair', 'Light', 'Angavu');
  String get themeDark => _t('Sombre', 'Dark', 'Giza');
  String get themeSystem => _t('Système', 'System', 'Mfumo');
  String get others => _t('Autres', 'Other', 'Nyingine');
  String get developedBy =>
      _t('Développé par', 'Developed by', 'Imetengenezwa na');
  String get helpSupport =>
      _t('Aide et support', 'Help & support', 'Msaada');
  String get logout => _t('Déconnexion', 'Log out', 'Toka');
  String get logoutConfirmTitle => logout;
  String get logoutConfirmBody => _t(
        'Voulez-vous vraiment vous déconnecter ?',
        'Do you really want to log out?',
        'Je, unataka kweli kutoka?',
      );
  String get cancel => _t('Annuler', 'Cancel', 'Ghairi');
  String get changeProfilePhoto => _t(
        'Photo de profil',
        'Profile photo',
        'Picha ya wasifu',
      );
  String get chooseFromGallery => _t(
        'Choisir dans la galerie',
        'Choose from gallery',
        'Chagua kutoka kwenye galeria',
      );
  String get takePhoto => _t(
        'Prendre une photo',
        'Take a photo',
        'Piga picha',
      );
  String get removePhoto => _t(
        'Supprimer la photo',
        'Remove photo',
        'Ondoa picha',
      );
  String get photoPickFailed => _t(
        'Impossible d’obtenir la photo. Réessayez.',
        'Could not get the photo. Please try again.',
        'Imeshindikana kupata picha. Jaribu tena.',
      );
  String get copied => _t(
        'Copié dans le presse-papiers.',
        'Copied to clipboard.',
        'Imenakiliwa.',
      );

  // —— Infos personnelles ——
  String get fullName => _t('Nom complet', 'Full name', 'Jina kamili');
  String get firstName => _t('Prénom', 'First name', 'Jina la kwanza');
  String get lastName => _t('Nom', 'Last name', 'Jina la familia');
  String get postName => _t('Postnom', 'Middle name', 'Jina la kati');
  String get gender => _t('Sexe', 'Gender', 'Jinsia');
  String get phone => _t('Téléphone', 'Phone', 'Simu');
  String get phoneSecondary =>
      _t('Téléphone secondaire', 'Secondary phone', 'Simu ya pili');
  String get email => _t('E-mail', 'Email', 'Barua pepe');
  String get profession => _t('Profession', 'Profession', 'Kazi');
  String get address => _t('Adresse', 'Address', 'Anwani');
  String get idNumber =>
      _t('N° d’identification', 'ID number', 'Nambari ya kitambulisho');
  String get personalInfoHint => _t(
        'Pour modifier ces informations, contactez le secrétariat de votre établissement.',
        'To update this information, contact your school secretariat.',
        'Ili kubadilisha taarifa hizi, wasiliana na sekretarieti ya shule yako.',
      );

  // —— Aide ——
  String get contactSchool =>
      _t('Contacter l’école', 'Contact the school', 'Wasiliana na shule');
  String get schoolHours =>
      _t('Horaires secrétariat', 'Office hours', 'Saa za ofisi');
  String get faqTitle =>
      _t('Questions fréquentes', 'Frequently asked questions', 'Maswali ya kawaida');
  String get faqLoginQ =>
      _t('Comment me connecter ?', 'How do I sign in?', 'Naingiaje?');
  String get faqLoginA => _t(
        'Utilisez le numéro de téléphone enregistré au secrétariat et votre numéro d’identification parent.',
        'Use the phone number registered at the secretariat and your parent ID number.',
        'Tumia nambari ya simu iliyosajiliwa katika sekretarieti na nambari yako ya kitambulisho cha mzazi.',
      );
  String get faqModulesQ => _t(
        'Où voir les notes et absences ?',
        'Where can I see grades and absences?',
        'Naweza kuona wapi alama na kutokuwepo?',
      );
  String get faqModulesA => _t(
        'Onglet Mes Enfants → choisissez l’élève → Présence, Absences, Discipline ou Paiement.',
        'My Children tab → select the student → Attendance, Absences, Discipline or Payments.',
        'Kichupo Watoto wangu → chagua mwanafunzi → Mahudhurio, Kutokuwepo, Nidhamu au Malipo.',
      );
  String get faqNotifQ => _t(
        'Les notifications ne s’affichent pas ?',
        'Notifications are not showing?',
        'Arifa hazionekani?',
      );
  String get faqNotifA => _t(
        'Tirez pour actualiser l’écran Notifications. Si le problème continue, contactez le secrétariat.',
        'Pull to refresh the Notifications screen. If it continues, contact the secretariat.',
        'Vuta ili kuonyesha upya skrini ya Arifa. Ikiendelea, wasiliana na sekretarieti.',
      );
  String get faqEditQ => _t(
        'Comment corriger mon nom ou mon e-mail ?',
        'How do I correct my name or email?',
        'Ninawezaje kusahihisha jina au barua pepe?',
      );
  String get faqEditA => _t(
        'Seul le secrétariat peut modifier votre fiche. Passez au bureau ou appelez les numéros ci-dessus.',
        'Only the secretariat can update your record. Visit the office or call the numbers above.',
        'Sekretarieti pekee inaweza kubadilisha rekodi yako. Tembelea ofisi au piga nambari zilizo hapo juu.',
      );

  // —— Accueil ——
  String get hello => _t('Bonjour,', 'Hello,', 'Habari,');
  String get welcomeSchool => _t(
        'Bienvenue sur ELIMU Go',
        'Welcome to ELIMU Go',
        'Karibu ELIMU Go',
      );
  String get overview => _t('Vue d’ensemble', 'Overview', 'Muhtasari');
  String get children => _t('Enfants', 'Children', 'Watoto');
  String get paidBalance =>
      _t('Soldes payés', 'Paid balance', 'Salio lililolipwa');
  String get unpaidBalance =>
      _t('Solde impayé', 'Unpaid balance', 'Salio lisilolipwa');
  String get filterNotifications =>
      _t('Filtrer', 'Filter', 'Chuja');
  String get recentActivities =>
      _t('Activités récentes', 'Recent activity', 'Shughuli za hivi karibuni');
  String get seeAll => _t('Voir tout', 'See all', 'Angalia zote');
  String get noRecentActivity => _t(
        'Aucune activité récente pour le moment.',
        'No recent activity yet.',
        'Hakuna shughuli za hivi karibuni bado.',
      );
  String get retry => _t('Réessayer', 'Retry', 'Jaribu tena');

  // —— Notifications ——
  String get notificationsTitle => navNotifications;
  String get filterAll => _t('Toutes', 'All', 'Zote');
  String get filterGeneral => _t('Générales', 'General', 'Jumla');
  String get filterSchool => _t('Scolaires', 'School', 'Shuleni');
  String get filterFinance => _t('Financières', 'Financial', 'Fedha');
  String get seeMore => _t('Voir plus', 'See more', 'Angalia zaidi');
  String get markAllAsRead =>
      _t('Tout marquer comme lu', 'Mark all as read', 'Weka zote zimesomwa');
  String get markedAllAsRead => _t(
        'Toutes les notifications sont marquées comme lues.',
        'All notifications marked as read.',
        'Arifa zote zimewekwa kuwa zimesomwa.',
      );
  String get noNotifications => _t(
        'Aucune notification pour le moment.',
        'No notifications yet.',
        'Hakuna arifa bado.',
      );
  String noNotificationsIn(String tab) => _t(
        'Aucune notification dans « $tab ».',
        'No notifications in “$tab”.',
        'Hakuna arifa katika “$tab”.',
      );
  String get scolairesHint => _t(
        'Présences, retards, convocations et discipline apparaissent ici.',
        'Attendance, lateness, summons and discipline appear here.',
        'Mahudhurio, kuchelewa, wito na nidhamu huonekana hapa.',
      );
  String get advancedFiltersSoon => _t(
        'Filtres avancés — à venir.',
        'Advanced filters — coming soon.',
        'Vichujio vya juu — vinakuja.',
      );

  // —— Enfants / divers ——
  String get myChildren => navChildren;
  String get aboutTitle => navAbout;

  // —— À propos ——
  String get presentation =>
      _t('Présentation', 'Presentation', 'Utangulizi');
  String get ourOptions =>
      _t('Nos options', 'Our options', 'Chaguzi zetu');
  String get ourLevels =>
      _t('Nos niveaux', 'Our levels', 'Ngazi zetu');
  String get contactUs =>
      _t('Nous contacter', 'Contact us', 'Wasiliana nasi');
  String get levelNursery => _t('Maternel', 'Nursery', 'Chekechea');
  String get levelPrimary => _t('Primaire', 'Primary', 'Msingi');
  String get levelSecondary =>
      _t('Secondaire', 'Secondary', 'Sekondari');
}
