"""
SERVICES_DATA : Version Premium (Stratégie & Expertise)
Ce dictionnaire contient l'ensemble des services du cabinet, 
optimisés pour une conversion client maximale.
"""

SERVICES_DATA = {
    "comptabilite": {
        "title": "Direction Comptable & Performance",
        "badge_category": "Gestion Financière",
        "hero_description": "La comptabilité n'est plus une contrainte, mais un moteur de décision. Nous transformons vos flux financiers en tableaux de bord stratégiques pour piloter votre rentabilité en temps réel et garantir une sérénité totale vis-à-vis des tiers.",
        "metric_title": "États financiers certifiés",
        "metric_value": "250+",
        "metric_suffix": " / an",
        "progress_percent": 95,
        "extra_label_1": "Standard",
        "extra_val_1": "SYSCOHADA Révisé",
        "extra_label_2": "Reporting",
        "extra_val_2": "Outils de Pilotage SMT",
        "motif_code": "COMPTABILITE_STRATEGIQUE",
        "pillars": [
            {
                "title": "Au-delà de la saisie",
                "desc": "Nous ne nous contentons pas de saisir des données ; nous construisons une infrastructure financière fiable et organisée.",
                "points": [
                    "Tenue et révision comptable complète (SYSCOHADA)",
                    "Automatisation des flux de trésorerie et rapprochements bancaires",
                    "Établissement des états financiers annuels (Bilan, Compte de résultat, SIG)",
                    "Gestion des immobilisations et amortissements",
                    "Reporting financier périodique pour aide à la décision"
                ]
            },
            {
                "title": "La maîtrise du risque",
                "desc": "Une comptabilité maîtrisée est votre meilleure défense juridique et votre atout principal face aux institutions bancaires.",
                "points": [
                    "Fiabilisation des comptes pour les audits externes",
                    "Sécurisation du cycle de clôture annuelle",
                    "Conformité rigoureuse aux normes comptables en vigueur",
                    "Interlocuteur privilégié pour vos commissaires aux comptes",
                    "Traçabilité totale des opérations"
                ]
            },
            {
                "title": "Le levier de performance",
                "desc": "Nos états financiers sont vos outils de pilotage. Nous analysons vos marges et votre structure de coûts pour booster votre rentabilité.",
                "points": [
                    "Analyse de la rentabilité par centre de profit",
                    "Conseil en optimisation du fonds de roulement (BFR)",
                    "Anticipation des besoins de financement",
                    "Tableaux de bord personnalisés",
                    "Accompagnement dans les choix d'investissements"
                ]
            }
        ],
        "faq": [
            {"q": "Mes données sont-elles protégées ?", "a": "La confidentialité est notre fondement. Vos données sont hébergées sur des serveurs sécurisés et accessibles uniquement par les collaborateurs dédiés, sous contrat de confidentialité strict."},
            {"q": "Pouvez-vous rattraper un historique comptable incomplet ?", "a": "C'est notre spécialité. Nous réalisons un diagnostic de l'existant, mettons à niveau vos comptes et régularisons le passé pour repartir sur des bases saines."},
            {"q": "Quelle est la fréquence de nos échanges ?", "a": "Nous adaptons notre rythme au vôtre : suivi mensuel, trimestriel ou en temps réel via nos outils de gestion partagée."}
        ]
    },
    "fiscalite": {
        "title": "Expertise Fiscale & Optimisation",
        "badge_category": "Stratégie Fiscale",
        "hero_description": "Ne subissez plus la pression fiscale. Nous sécurisons votre environnement fiscal tout en activant tous les leviers légaux d'optimisation pour maximiser votre cash-flow net.",
        "metric_title": "Taux de sécurité fiscale",
        "metric_value": "100",
        "metric_suffix": "%",
        "progress_percent": 100,
        "extra_label_1": "Domaine",
        "extra_val_1": "CGI Ivoirien & International",
        "extra_label_2": "Action",
        "extra_val_2": "Optimisation Proactive",
        "motif_code": "FISCALITE_INTEGRALE",
        "pillars": [
            {
                "title": "Gestion exhaustive des obligations",
                "desc": "Nous prenons en charge la totalité de votre portefeuille fiscal, sans omission, pour éliminer tout risque de redressement.",
                "points": [
                    "Déclarations périodiques complètes : TVA, BIC, ITS, CF, TPA, Retenues à la source",
                    "Gestion des taxes spécifiques liées à votre secteur d'activité",
                    "Établissement des liasses fiscales annuelles",
                    "Gestion des obligations déclaratives sociales et parafiscales",
                    "Veille réglementaire et fiscale quotidienne"
                ]
            },
            {
                "title": "Stratégie d'optimisation",
                "desc": "La fiscalité est un poste de coût majeur. Nous l'analysons pour réduire votre charge fiscale dans le respect strict de la loi.",
                "points": [
                    "Audit fiscal préventif pour identifier les économies d'impôt",
                    "Planification des paiements pour optimiser votre trésorerie",
                    "Conseil en structuration de projets pour minimiser l'impact fiscal",
                    "Utilisation des crédits et exonérations d'impôts éligibles",
                    "Simulation d'impact fiscal avant décisions stratégiques"
                ]
            },
            {
                "title": "Défense & Contentieux",
                "desc": "En cas de contrôle, nous ne vous abandonnons pas. Nous intervenons en première ligne pour protéger vos intérêts.",
                "points": [
                    "Assistance et conseil lors des contrôles fiscaux",
                    "Rédaction des réponses aux notifications de redressement",
                    "Gestion des recours et contentieux administratifs",
                    "Représentation auprès de l'administration fiscale",
                    "Analyse de la jurisprudence fiscale applicable"
                ]
            }
        ],
        "faq": [
            {"q": "Quelles taxes gérez-vous précisément ?", "a": "Nous couvrons l'ensemble du spectre fiscal : TVA, BIC (Bénéfices Industriels et Commerciaux), ITS (Impôt sur Traitements et Salaires), CF (Contribution des Patentes), TPA, et l'ensemble des taxes locales et annexes."},
            {"q": "Comment gérez-vous un contrôle fiscal ?", "a": "Nous prenons la main dès réception de l'avis. Nous préparons les documents, assistons aux réunions, et argumentons juridiquement chaque point pour limiter au maximum vos risques financiers."},
            {"q": "Est-ce légal d'optimiser ses impôts ?", "a": "Absolument. Il existe une différence fondamentale entre la fraude (illégale) et l'optimisation (utilisation intelligente des leviers prévus par le Code Général des Impôts). C'est notre rôle d'expert."}
        ]
    },
    "audit": {
        "title": "Audit & Diagnostic",
        "badge_category": "Transparence & Risque",
        "hero_description": "Découvrez vos failles avant qu'elles ne deviennent des handicaps. Notre audit est le révélateur de valeur qui assainit vos processus et sécurise vos actifs.",
        "metric_title": "Risques neutralisés",
        "metric_value": "99",
        "metric_suffix": " %",
        "progress_percent": 95,
        "extra_label_1": "Approche",
        "extra_val_1": "Indépendante",
        "extra_label_2": "Résultat",
        "extra_val_2": "Valeur ajoutée",
        "motif_code": "AUDIT_OPERATIONNEL",
        "pillars": [
            {
                "title": "Diagnostic 360°",
                "desc": "Une analyse chirurgicale de votre organisation pour identifier les inefficacités qui coûtent cher à votre entreprise.",
                "points": [
                    "Audit de fiabilité des procédures comptables",
                    "Évaluation des risques fiscaux et juridiques",
                    "Audit de contrôle interne et séparation des tâches",
                    "Diagnostic de performance organisationnelle",
                    "Vérification de la conformité réglementaire"
                ]
            },
            {
                "title": "Maîtrise des risques",
                "desc": "Nous transformons les faiblesses identifiées en opportunités de renforcement de votre gouvernance.",
                "points": [
                    "Cartographie des risques opérationnels",
                    "Évaluation de la solidité financière",
                    "Détection des anomalies de gestion et fraudes potentielles",
                    "Renforcement de la transparence vis-à-vis des parties prenantes",
                    "Sécurisation des processus de prise de décision"
                ]
            },
            {
                "title": "Solutions actionnables",
                "desc": "Un audit sans recommandations est inutile. Nous livrons des plans d'action pragmatiques et immédiats.",
                "points": [
                    "Rapport de mission clair avec priorités d'action",
                    "Accompagnement à la mise en œuvre des corrections",
                    "Optimisation des flux et des outils de gestion",
                    "Indépendance et objectivité garanties",
                    "Suivi post-audit pour mesurer les progrès"
                ]
            }
        ],
        "faq": [
            {"q": "L'audit est-il synonyme de sanction ?", "a": "Au contraire, c'est un outil de développement. Nous identifions ce qui ne fonctionne pas pour le corriger, afin de vous permettre de grandir plus sereinement et plus vite."},
            {"q": "Faut-il être une grande entreprise pour être audité ?", "a": "Pas du tout. Une PME qui se fait auditer tôt évite des erreurs critiques qui pourraient paralyser son développement futur. C'est un investissement pour la pérennité."}
        ]
    },
    "rh": {
        "title": "Gestion Sociale & RH",
        "badge_category": "Gestion Sociale",
        "hero_description": "Le capital humain est votre actif le plus précieux. Sécurisez vos relations contractuelles, automatisez votre paie et assurez une conformité totale avec le code du travail.",
        "metric_title": "Bulletins traités",
        "metric_value": "500+",
        "metric_suffix": " / mois",
        "progress_percent": 100,
        "extra_label_1": "Focus",
        "extra_val_1": "Conformité Sociale",
        "extra_label_2": "Outil",
        "extra_val_2": "Paie sécurisée",
        "motif_code": "RH_SOCIAL",
        "pillars": [
            {
                "title": "Gestion de la paie",
                "desc": "Une paie erronée est la source numéro un de conflits. Nous garantissons une précision chirurgicale.",
                "points": [
                    "Établissement des bulletins de paie automatisés",
                    "Calcul des charges sociales (CNPS, IS, etc.)",
                    "Gestion des congés, primes et indemnités",
                    "Déclarations sociales périodiques",
                    "Suivi des dossiers individuels du personnel"
                ]
            },
            {
                "title": "Conseil en droit du travail",
                "desc": "Le cadre juridique social est complexe. Nous vous accompagnons pour sécuriser vos relations employeur-employé.",
                "points": [
                    "Rédaction et audit des contrats de travail",
                    "Gestion des procédures disciplinaires",
                    "Accompagnement lors des ruptures de contrat",
                    "Mise en conformité avec le Code du Travail",
                    "Veille sur les conventions collectives"
                ]
            },
            {
                "title": "Stratégie RH",
                "desc": "Nous aidons à structurer votre département RH pour soutenir votre croissance.",
                "points": [
                    "Mise en place de procédures de recrutement",
                    "Définition des fiches de poste",
                    "Optimisation des coûts salariaux",
                    "Gestion des relations avec les représentants du personnel",
                    "Digitalisation des processus RH"
                ]
            }
        ],
        "faq": [
            {"q": "Gérez-vous les effectifs réduits ?", "a": "Oui, nous accompagnons aussi bien les structures avec un seul salarié que les PME à effectifs plus importants. La précision reste la même."},
            {"q": "Comment gérez-vous les contentieux prud'homaux ?", "a": "Nous agissons en prévention pour les éviter. Si un litige survient, nous vous accompagnons pour préparer les dossiers et limiter votre exposition au risque."}
        ]
    },
    "formation": {
        "title": "Formations & Transfert de Compétences",
        "badge_category": "Formation",
        "hero_description": "Ne dépendez plus de prestataires externes. Nous formons vos équipes pour qu'elles maîtrisent leurs outils de gestion et deviennent autonomes et performantes.",
        "metric_title": "Experts formés",
        "metric_value": "450+",
        "metric_suffix": " collaborateurs",
        "progress_percent": 90,
        "extra_label_1": "Logiciels",
        "extra_val_1": "Sage, SAARI, Excel",
        "extra_label_2": "Format",
        "extra_val_2": "Pratique & Terrain",
        "motif_code": "FORMATION_EXPERT",
        "pillars": [
            {
                "title": "Maîtrise des outils",
                "desc": "Nous formons vos équipes sur les logiciels de référence du marché pour une gestion fluide.",
                "points": [
                    "Formation pratique sur Sage/SAARI (Compta/Paie)",
                    "Maîtrise d'Excel pour la gestion financière",
                    "Optimisation de l'utilisation des logiciels de gestion interne",
                    "Automatisation des tâches récurrentes",
                    "Formation à la lecture des états financiers"
                ]
            },
            {
                "title": "Montée en compétence",
                "desc": "Nous transformons vos employés en collaborateurs capables d'analyser et d'agir.",
                "points": [
                    "Ateliers de gestion financière pour non-financiers",
                    "Formation sur le Code Général des Impôts pratique",
                    "Gestion des procédures administratives",
                    "Techniques de reporting et tableau de bord",
                    "Gestion du temps et organisation"
                ]
            },
            {
                "title": "La méthode K&L",
                "desc": "Nous ne faisons pas de la théorie. Nous formons sur VOS données et VOS problématiques réelles.",
                "points": [
                    "Formations sur mesure adaptées au niveau des équipes",
                    "Études de cas réels basés sur votre activité",
                    "Accompagnement post-formation pour mise en pratique",
                    "Supports de cours opérationnels",
                    "Évaluation des acquis et suivi"
                ]
            }
        ],
        "faq": [
            {"q": "Les formations sont-elles collectives ou individuelles ?", "a": "Nous proposons les deux. L'individuel pour un besoin spécifique (ex: un nouveau comptable) ou le collectif pour harmoniser les pratiques de toute une équipe."},
            {"q": "Faites-vous des formations sur-mesure ?", "a": "Oui, c'est notre marque de fabrique. Nous analysons vos besoins et construisons le programme de formation qui répond exactement à vos défis."}
        ]
    },
    "conseil": {
        "title": "Conseil en Gestion & Procédures",
        "badge_category": "Stratégie & Conseil",
        "hero_description": "Structurez votre entreprise pour passer à l'échelle. Nous traduisons vos visions en manuels de procédures clairs, efficaces et immédiatement opérationnels.",
        "metric_title": "Manuels implémentés",
        "metric_value": "80+",
        "metric_suffix": " procédures",
        "progress_percent": 95,
        "extra_label_1": "Approche",
        "extra_val_1": "Pragmatisme",
        "extra_label_2": "Résultat",
        "extra_val_2": "Gain d'efficacité",
        "motif_code": "CONSEIL_STRATEGIQUE",
        "pillars": [
            {
                "title": "Diagnostic & Restructuration",
                "desc": "Nous identifions les blocages organisationnels pour libérer votre potentiel de croissance.",
                "points": [
                    "Audit organisationnel complet",
                    "Réorganisation des flux d'information",
                    "Études de faisabilité de nouveaux projets",
                    "Diagnostic de performance des processus",
                    "Accompagnement à la conduite du changement"
                ]
            },
            {
                "title": "Ingénierie des procédures",
                "desc": "Des processus clairs sont le socle de la scalabilité. Nous documentons votre savoir-faire.",
                "points": [
                    "Rédaction de manuels de procédures comptables",
                    "Structuration des processus d'achat/vente",
                    "Mise en place de procédures de contrôle interne",
                    "Formalisation des circuits de validation",
                    "Création d'outils de gestion de projet"
                ]
            },
            {
                "title": "Pragmatisme opérationnel",
                "desc": "Nous ne rédigeons pas pour le tiroir. Nous créons des outils de travail utilisés au quotidien.",
                "points": [
                    "Focus sur la simplicité et l'applicabilité",
                    "Alignement des procédures avec la culture d'entreprise",
                    "Formation des équipes aux nouvelles procédures",
                    "Suivi de l'appropriation des outils",
                    "Ajustement continu basé sur les retours terrain"
                ]
            }
        ],
        "faq": [
            {"q": "Quelle est la différence avec de la formation ?", "a": "Le conseil intervient sur la structure et l'organisation, tandis que la formation intervient sur le savoir-faire des collaborateurs."},
            {"q": "Est-ce applicable aux petites entreprises ?", "a": "C'est même recommandé. Mettre en place des procédures dès le début permet d'éviter la désorganisation lors des phases de forte croissance."}
        ]
    },
    "strategie": {
        "title": "Gouvernance & Stratégie",
        "badge_category": "Gouvernance",
        "hero_description": "Pilotez votre entreprise comme un leader. Nous apportons la rigueur et la vision externe nécessaires pour sécuriser votre pérennité et réussir vos transitions stratégiques.",
        "metric_title": "Plans stratégiques",
        "metric_value": "40+",
        "metric_suffix": " déployés",
        "progress_percent": 100,
        "extra_label_1": "Expertise",
        "extra_val_1": "Vision externe",
        "extra_label_2": "Spécialité",
        "extra_val_2": "Fusion & Acquisition",
        "motif_code": "STRATEGIE_GOVERNANCE",
        "pillars": [
            {
                "title": "Vision & Gouvernance",
                "desc": "Nous agissons comme un board externe pour challenger vos décisions et structurer votre vision à long terme.",
                "points": [
                    "Planification stratégique pluriannuelle",
                    "Structuration de la gouvernance d'entreprise",
                    "Conseil aux dirigeants et actionnaires",
                    "Alignement des objectifs opérationnels avec la stratégie",
                    "Gestion de la croissance pérenne"
                ]
            },
            {
                "title": "Opérations complexes",
                "desc": "Nous vous accompagnons sur les décisions qui engagent l'avenir de votre structure.",
                "points": [
                    "Accompagnement lors des opérations de fusion-acquisition",
                    "Due diligence financière et fiscale",
                    "Valorisation d'entreprise",
                    "Structuration de partenariats stratégiques",
                    "Gestion des cessions et transmissions"
                ]
            },
            {
                "title": "Rigueur & Confiance",
                "desc": "Une gouvernance saine est la clé pour attirer investisseurs et partenaires bancaires.",
                "points": [
                    "Renforcement de la transparence vis-à-vis des tiers",
                    "Sécurisation des décisions stratégiques",
                    "Conformité aux standards de gouvernance",
                    "Reporting de haut niveau pour les actionnaires",
                    "Expertise transactionnelle"
                ]
            }
        ],
        "faq": [
            {"q": "Intervenez-vous uniquement lors de fusions ?", "a": "Absolument pas. L'essentiel de notre travail porte sur la structuration quotidienne de la gouvernance, pour éviter justement les problèmes lors des transitions futures."},
            {"q": "Faut-il avoir un organigramme pour vous consulter ?", "a": "Non. Nous partons souvent d'une page blanche pour concevoir, avec vous, l'organisation la plus adaptée à votre taille et à vos ambitions."}
        ]
    },
    "financement": {
        "title": "Ingénierie Financière & Levée de Fonds",
        "badge_category": "Financement",
        "hero_description": "Ne laissez pas le manque de financement freiner votre ambition. Nous transformons vos projets en dossiers bancables pour accéder aux ressources nécessaires à votre développement.",
        "metric_title": "Taux de succès",
        "metric_value": "90",
        "metric_suffix": " %",
        "progress_percent": 95,
        "extra_label_1": "Succès",
        "extra_val_1": "Dossiers financés",
        "extra_label_2": "Réseau",
        "extra_val_2": "Bailleurs & Banques",
        "motif_code": "FINANCEMENT_CROISSANCE",
        "pillars": [
            {
                "title": "Ingénierie de financement",
                "desc": "Nous identifions et activons les leviers de financement adaptés à chaque stade de votre projet.",
                "points": [
                    "Identification des subventions et financements publics",
                    "Montage de business plans de haut niveau",
                    "Préparation des dossiers bancaires (crédit, découvert, leasing)",
                    "Structuration des plans de financement",
                    "Reporting financier pour les bailleurs"
                ]
            },
            {
                "title": "Crédibilité financière",
                "desc": "Un dossier bien monté est un dossier financé. Nous rédigeons avec la rigueur attendue par les financeurs.",
                "points": [
                    "Analyse de la capacité d'endettement",
                    "Présentation financière persuasive et cohérente",
                    "Modélisation prévisionnelle robuste",
                    "Soutenance de dossiers devant les partenaires",
                    "Optimisation de la structure financière"
                ]
            },
            {
                "title": "Accompagnement durable",
                "desc": "Nous vous accompagnons au-delà de l'obtention du financement pour garantir la bonne exécution des engagements.",
                "points": [
                    "Gestion des relations bailleurs",
                    "Suivi de l'utilisation des fonds obtenus",
                    "Reporting conforme aux exigences des partenaires",
                    "Ajustement des plans de financement",
                    "Conseil en gestion de trésorerie post-financement"
                ]
            }
        ],
        "faq": [
            {"q": "Mon entreprise est jeune, puis-je prétendre à des financements ?", "a": "Oui. C'est précisément à ce stade que notre expertise est la plus valorisée : nous construisons le dossier qui rassurera les banques et investisseurs sur votre potentiel."},
            {"q": "Gérez-vous aussi les financements privés ?", "a": "Tout à fait. Nous préparons les dossiers pour les banques classiques, les institutions de microfinance, et accompagnons la préparation à la levée de fonds auprès d'investisseurs privés."}
        ]
    }
}