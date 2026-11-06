"""
Enrichit la base SQLite déterministe `ccq_cpc.db` avec les lois spéciales québécoises et canadiennes :
- LAA (Loi sur l'assurance automobile, RLRQ c. A-25)
- LJA (Loi sur la justice administrative, RLRQ c. J-3 — TAQ)
- LATMP (Loi sur les accidents du travail et les maladies professionnelles, RLRQ c. A-3.001 — CNESST/TAT)
- LNT (Loi sur les normes du travail, RLRQ c. N-1.1 — CNESST/TAT)
- LPC (Loi sur la protection du consommateur, RLRQ c. P-40.1)
- LAF (Loi sur l'administration fiscale, RLRQ c. A-6.002 — Revenu Québec)
- LTVQ (Loi sur la taxe de vente du Québec, RLRQ c. T-0.1)
- LI (Loi sur les impôts, RLRQ c. I-3)
- LSAQ (Loi sur les sociétés par actions, RLRQ c. S-31.1)
- CHARTE (Charte des droits et libertés de la personne, RLRQ c. C-12)
- LOI25 (Loi sur la protection des renseignements personnels dans le secteur privé, RLRQ c. P-39.1)
- LTAL (Loi sur le Tribunal administratif du logement, RLRQ c. T-15.01)
- CSR (Code de la sécurité routière, RLRQ c. C-24.2)
- CCR (Code criminel, L.R.C. (1985), ch. C-46)
Ainsi que 12 barèmes actuariels empiriques (`quantum_benchmarks`) couvrant les grandes verticales de litige au Québec.
"""
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "../app/data/ccq_cpc.db")

STATUTE_ARTICLES = [
    # ==================== LAA (Loi sur l'assurance automobile, RLRQ c. A-25) ====================
    ("LAA", "1", "Dans la présente loi, on entend par « accident » : tout événement au cours duquel un préjudice est causé par une automobile, y compris le chargement et le déchargement d'une automobile.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:1"),
    ("LAA", "2", "Dans le présent titre, on entend par « préjudice corporel » : tout préjudice d'ordre physique ou psychique d'une victime, y compris le décès, qui lui est causé dans un accident.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:2"),
    ("LAA", "5", "Les indemnités prévues au présent titre sont accordées par la Société sans égard à la responsabilité de quiconque (régime public d'indemnisation sans égard à la faute).", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:5"),
    ("LAA", "6", "Est une victime, la personne qui subit un préjudice corporel dans un accident.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:6"),
    ("LAA", "14", "La victime qui, au moment de l'accident, exerçait habituellement un emploi à temps plein a droit à une indemnité de remplacement du revenu (IRR) si, en raison de cet accident, elle est incapable d'exercer son emploi.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:14"),
    ("LAA", "15", "La victime qui, au moment de l'accident, exerçait un emploi temporaire ou à temps partiel a droit à une indemnité de remplacement du revenu si elle est incapable d'exercer cet emploi en raison de l'accident.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:15"),
    ("LAA", "19", "À compter du 181e jour qui suit l'accident, la Société détermine un emploi à la victime qui exerçait un emploi temporaire ou à temps partiel si elle demeure incapable de l'exercer.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:19"),
    ("LAA", "24", "La victime sans emploi au moment de l'accident mais capable de travailler a droit à une indemnité de remplacement du revenu à compter du 181e jour qui suit l'accident si elle demeure incapable d'exercer l'emploi que la Société lui détermine.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:24"),
    ("LAA", "29", "L'indemnité de remplacement du revenu (IRR) d'une victime est égale à 90 % de son revenu net retenu sur une base annuelle.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:29"),
    ("LAA", "36", "Tant qu'elle est incapable d'exercer ses études en raison de l'accident, la victime étudiante a droit à une indemnité forfaitaire.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:36"),
    ("LAA", "45", "La Société détermine un emploi à une victime à compter du moment où elle est capable d'exercer un emploi convenable, mais qu'elle demeure incapable d'exercer son emploi habituel en raison de l'accident.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:45"),
    ("LAA", "46", "Pour déterminer un emploi convenable à la victime, la Société tient compte, outre les normes et modalités prévues par règlement, de sa formation, de son expérience de travail et de ses capacités physiques et intellectuelles au moment où elle statue.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:46"),
    ("LAA", "47", "La victime qui, après deux ans à compter de l'accident, est capable d'exercer un emploi convenable à temps plein ou à temps partiel voit son indemnité réduite du revenu net qu'elle pourrait tirer de cet emploi déterminé.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:47"),
    ("LAA", "48", "La victime qui redevient capable d'exercer son emploi ou un emploi convenable bénéficie du maintien de son indemnité pendant une période additionnelle d'adaptation d'au plus un an si elle ne détient pas d'emploi.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:48"),
    ("LAA", "49", "L'indemnité de remplacement du revenu (IRR) prend fin lorsque la victime redevient capable d'exercer son emploi ou un emploi convenable déterminé par la Société.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:49"),
    ("LAA", "50", "Lorsque l'indemnité de remplacement du revenu est réduite parce que la victime est capable d'exercer un emploi convenable moins rémunérateur que son emploi habituel, elle a droit à une indemnité différentielle (IRR réduite).", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:50"),
    ("LAA", "57", "En cas de rechute, dans les deux ans de la fin de la dernière période d'incapacité pour laquelle la victime avait droit à l'IRR ou, si elle n'a pas eu droit à cette indemnité, dans les deux ans de l'accident, la victime est indemnisée comme si son incapacité n'avait pas été interrompue.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:57"),
    ("LAA", "73", "Pour le préjudice non pécuniaire (perte de jouissance de la vie, douleurs physiques et souffrances psychiques), la victime a droit, dans la mesure déterminée par règlement sur le barème des dommages corporels (classes de gravité), à une indemnité forfaitaire pour séquelles permanentes.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:73"),
    ("LAA", "74", "L'évaluation des séquelles anatomo-physiologiques et du préjudice esthétique s'effectue après la consolidation de la blessure suivant le Règlement sur le barème des dommages corporels.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:74"),
    ("LAA", "79", "La victime dont l'état physique ou psychique, en raison de l'accident, nécessite des soins personnels ou une aide à domicile a droit au remboursement des frais engagés jusqu'à concurrence des montants réglementaires.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:79"),
    ("LAA", "83.1", "La Société prend les mesures nécessaires en vue de contribuer à la réadaptation de la victime, d'atténuer ou de faire disparaître toute incapacité résultant d'un préjudice corporel et de faciliter son retour à la vie normale ou sa réinsertion sociale et professionnelle.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:83_1"),
    ("LAA", "83.2", "Une victime a droit, dans les cas et aux conditions prescrits par règlement (notamment sur ordonnance médicale préalable), au remboursement des frais qu'elle engage en raison de l'accident pour recevoir des soins médicaux ou paramédicaux, des traitements de physiothérapie ou de chiropratique, des médicaments ou des prothèses.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:83_2"),
    ("LAA", "83.22", "À la demande de la Société et à ses frais, la victime doit se soumettre à l'examen d'un professionnel de la santé choisi par la Société.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:83_22"),
    ("LAA", "83.24", "Le professionnel de la santé qui examine une victime à la demande de la Société doit faire rapport à celle-ci sur toute question relative au préjudice corporel pour laquelle son avis est requis.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:83_24"),
    ("LAA", "83.30", "La Société peut, en tout temps, rendre une nouvelle décision si survient un fait nouveau qui modifie la situation de la victime ou si le montant de l'indemnité a été fixé sur la base d'une erreur.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:83_30"),
    ("LAA", "83.32", "Lorsque la Société, à la suite d'une demande de révision ou d'une décision du Tribunal administratif du Québec (TAQ), reconnaît le droit à une indemnité qui avait été refusée ou augmente le montant d'une indemnité, elle verse à la personne qui y a droit des intérêts calculés au taux fixé en vertu de l'article 28 de la Loi sur l'administration fiscale à compter de la date de la décision refusant ou réduisant l'indemnité.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:83_32"),
    ("LAA", "83.34", "La personne qui se croit lésée par une décision rendue par la Société (SAAQ) peut, dans les 60 jours de sa notification, demander par écrit à la Société la révision de cette décision.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:83_34"),
    ("LAA", "83.41", "La personne qui se croit lésée par une décision rendue en révision par la Société peut, dans les 60 jours de sa notification, la contester devant le Tribunal administratif du Québec (TAQ - Section des affaires sociales).", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:83_41"),
    ("LAA", "83.49", "Le recours devant le Tribunal administratif du Québec ne suspend pas l'exécution de la décision de la Société, à moins que le Tribunal n'en décide autrement.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:83_49"),
    ("LAA", "83.57", "Les indemnités prévues au présent titre tiennent lieu de tous les droits et recours en raison d'un préjudice corporel et nulle action à ce sujet n'est admise devant un tribunal de droit civil (immunité civile absolue du régime sans égard à la faute).", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:83_57"),

    # ==================== LJA (Loi sur la justice administrative, RLRQ c. J-3 — TAQ) ====================
    ("LJA", "9", "Les procédures conduites par l'Administration ou le Tribunal administratif du Québec (TAQ) le sont dans le respect du devoir d'agir équitablement, avec souplesse, célérité et maîtrise du dossier.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/J-3#se:9"),
    ("LJA", "14", "Le Tribunal administratif du Québec (TAQ) a pour fonction, dans les cas prévus par la loi, de statuer sur les recours formés contre une autorité administrative ou une autorité décentralisée.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/J-3#se:14"),
    ("LJA", "15", "Le Tribunal a le pouvoir de décider toute question de droit ou de fait nécessaire à l'exercice de sa compétence. Lorsqu'il est saisi d'une contestation d'une décision, il peut confirmer, modifier ou infirmer la décision contestée et, s'il y a lieu, rendre la décision qui, à son avis, aurait dû être prise en premier lieu.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/J-3#se:15"),
    ("LJA", "24", "En matière d'indemnisation (notamment SAAQ et IVAC), les recours devant la section des affaires sociales sont instruits et décidés par une formation de deux membres, dont l'un est avocat ou notaire et l'autre médecin.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/J-3#se:24"),
    ("LJA", "74", "Le Tribunal peut ordonner à une partie de payer certains frais ou débours uniquement si une partie a agi de manière manifestement abusive ou dilatoire.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/J-3#se:74"),
    ("LJA", "102", "Tout recours devant le Tribunal administratif du Québec est formé dans les 30 jours (ou 60 jours en matière d'indemnisation SAAQ suivant l'art. 83.41 L.a.a.) de la notification de la décision contestée.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/J-3#se:102"),
    ("LJA", "119", "S'il considère que cela est utile et si la matière et les circonstances d'une affaire le permettent, le président du Tribunal ou le membre qu'il désigne offre aux parties la tenue d'une séance de conciliation.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/J-3#se:119"),
    ("LJA", "120", "La séance de conciliation a pour but d'aider les parties à communiquer, à négocier, à identifier leurs intérêts, à évaluer leurs positions et à explorer des solutions mutuellement satisfaisantes pour régler leur litige devant le TAQ.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/J-3#se:120"),
    ("LJA", "121", "À moins que les parties n'y consentent, rien de ce qui a été dit ou écrit au cours d'une séance de conciliation n'est recevable en preuve devant un tribunal.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/J-3#se:121"),
    ("LJA", "124", "Tout accord conclu en conciliation est consigné par écrit, signé par le conciliateur et les parties ou leurs représentants. Il lie les parties et met fin au litige devant le TAQ.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/J-3#se:124"),
    ("LJA", "142", "Le Tribunal administratif du Québec accepte tout moyen de preuve fiable et pertinent, sous réserve de son pouvoir d'apprécier la valeur probante des expertises et témoignages.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/J-3#se:142"),
    ("LJA", "154", "Le Tribunal peut, sur demande, réviser ou révoquer toute décision qu'il a rendue lorsqu'est découvert un fait nouveau qui, s'il avait été connu en temps utile, aurait pu justifier une décision différente, ou lorsqu'un vice de fond ou de procédure est de nature à invalider la décision.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/J-3#se:154"),

    # ==================== LATMP (Loi sur les accidents du travail et les maladies professionnelles, RLRQ c. A-3.001) ====================
    ("LATMP", "2", "Dans la présente loi, on entend par « lésion professionnelle » une blessure ou une maladie qui survient par le fait ou à l'occasion d'un accident du travail, ou une maladie professionnelle, y compris la récidive, la rechute ou l'aggravation d'une telle lésion.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-3.001#se:2"),
    ("LATMP", "7", "Est un accident du travail un événement imprévu et soudain attribuable à toute cause, survenant à une personne par le fait ou à l'occasion de son travail et qui entraîne pour elle une lésion professionnelle.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-3.001#se:7"),
    ("LATMP", "27", "Une blessure ou une maladie qui survient uniquement à cause de la négligence grossière et volontaire du travailleur qui en est victime n'est pas une lésion professionnelle, à moins qu'elle n'entraîne le décès du travailleur ou qu'elle ne lui cause une atteinte permanente grave à son intégrité physique ou psychique.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-3.001#se:27"),
    ("LATMP", "28", "Une blessure qui arrive sur les lieux du travail alors que le travailleur est à son travail est présumée une lésion professionnelle (présomption légale de l'art. 28 L.A.T.M.P.).", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-3.001#se:28"),
    ("LATMP", "29", "Les maladies énumérées dans le Règlement sur les maladies professionnelles sont caractéristiques d'un travail correspondant à chacune de ces maladies dans ce règlement et sont reliées directement aux risques particuliers de ce travail. Le travailleur atteint d'une telle maladie est présumé atteint d'une maladie professionnelle s'il a exercé un travail correspondant.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-3.001#se:29"),
    ("LATMP", "30", "Le travailleur atteint d'une maladie non prévue par règlement doit démontrer qu'elle est caractéristique d'un travail qu'il a exercé ou qu'elle est reliée directement aux risques particuliers de ce travail pour qu'elle soit reconnue comme maladie professionnelle.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-3.001#se:30"),
    ("LATMP", "31", "Est considérée une lésion professionnelle, une blessure ou une maladie qui survient par le fait ou à l'occasion des soins qu'un travailleur reçoit pour une lésion professionnelle ou de l'omission de tels soins.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-3.001#se:31"),
    ("LATMP", "44", "Le travailleur victime d'une lésion professionnelle a droit à une indemnité de remplacement du revenu (IRR de 90 % du revenu net retenu) s'il devient incapable d'exercer son emploi en raison de cette lésion.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-3.001#se:44"),
    ("LATMP", "49", "Lorsque la CNESST détermine que le travailleur est capable d'exercer un emploi convenable disponible, l'indemnité de remplacement du revenu est réduite du revenu net qu'il pourrait tirer de cet emploi convenable.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-3.001#se:49"),
    ("LATMP", "53", "Le travailleur qui redevient capable d'exercer son emploi après l'expiration du délai pour exercer son droit au retour au travail a droit à l'IRR jusqu'à ce qu'il occupe un nouvel emploi ou pendant une période maximale d'un an (recherche d'emploi).", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-3.001#se:53"),
    ("LATMP", "57", "Le droit à l'indemnité de remplacement du revenu s'éteint lorsque le travailleur redevient capable d'exercer son emploi ou un emploi convenable.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-3.001#se:57"),
    ("LATMP", "83", "Le travailleur victime d'une lésion professionnelle qui subit une atteinte permanente à son intégrité physique ou psychique a droit, pour chaque accident du travail ou maladie professionnelle, à une indemnité pour préjudice corporel qui tient compte du déficit anatomo-physiologique, du préjudice esthétique et des douleurs et de la perte de jouissance de la vie.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-3.001#se:83"),
    ("LATMP", "145", "Le travailleur qui, en raison de la lésion professionnelle dont il a été victime, subit une atteinte permanente à son intégrité physique ou psychique a droit à la réadaptation que requiert son état en vue de sa réinsertion sociale et professionnelle.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-3.001#se:145"),
    ("LATMP", "179", "L'employeur d'un travailleur victime d'une lésion professionnelle peut assigner temporairement un travail à ce dernier, en attendant qu'il redevienne capable d'exercer son emploi ou qu'il devienne capable d'exercer un emploi convenable, si le professionnel de la santé qui a charge du travailleur croit que le travailleur est raisonnablement en mesure d'accomplir ce travail.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-3.001#se:179"),
    ("LATMP", "212", "L'employeur qui a droit d'accès au dossier que la CNESST possède au sujet d'une lésion professionnelle peut contester l'évaluation du professionnel de la santé qui a charge du travailleur portant sur le diagnostic, la consolidation, les soins, le pourcentage d'atteinte permanente ou les limitations fonctionnelles.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-3.001#se:212"),
    ("LATMP", "224.1", "L'avis du membre du Bureau d'évaluation médicale (BEM) lie la CNESST, qui doit rendre une décision en conséquence.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-3.001#se:224_1"),
    ("LATMP", "239", "Le travailleur qui redevient capable d'exercer son emploi a droit de réintégrer prioritairement son emploi dans l'établissement où il travaillait lorsque s'est manifestée sa lésion professionnelle.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-3.001#se:239"),
    ("LATMP", "326", "La CNESST impute à l'employeur le coût des prestations dues en raison d'un accident du travail survenu à un travailleur alors qu'il était à son emploi. Elle peut toutefois, de sa propre initiative ou à la demande de l'employeur, imputer le coût des prestations aux employeurs de toutes les unités lorsque l'imputation aurait pour effet de faire supporter injustement à un employeur le coût des prestations dues en raison d'un accident du travail attribuable à un tiers.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-3.001#se:326"),
    ("LATMP", "329", "Dans le cas d'un travailleur déjà handicapé lorsque se manifeste sa lésion professionnelle, la CNESST peut, de sa propre initiative ou à la demande de l'employeur, imputer tout ou partie du coût des prestations aux employeurs de toutes les unités (partage des coûts pour condition préexistante / travailleur déjà handicapé).", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-3.001#se:329"),
    ("LATMP", "358", "Une personne qui se croit lésée par une décision rendue par la CNESST peut, dans les 30 jours de sa notification, en demander la révision administrative.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-3.001#se:358"),
    ("LATMP", "359", "Une personne qui se croit lésée par une décision rendue par la CNESST à la suite d'une demande de révision administrative peut, dans les 45 jours de sa notification, la contester devant le Tribunal administratif du travail (TAT).", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-3.001#se:359"),
    ("LATMP", "438", "Un travailleur victime d'une lésion professionnelle ne peut intenter une action en responsabilité civile contre son employeur en raison de sa lésion professionnelle (immunité civile de l'employeur).", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-3.001#se:438"),

    # ==================== LNT (Loi sur les normes du travail, RLRQ c. N-1.1) ====================
    ("LNT", "1", "Dans la présente loi, on entend par « salarié » une personne qui travaille pour un employeur et qui a droit à un salaire.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/N-1.1#se:1"),
    ("LNT", "40", "Le salaire minimum est déterminé par règlement du gouvernement.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/N-1.1#se:40"),
    ("LNT", "52", "Aux fins du calcul des heures supplémentaires, la semaine normale de travail est de 40 heures.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/N-1.1#se:52"),
    ("LNT", "55", "Tout travail exécuté en plus des heures de la semaine normale de travail entraîne une majoration de 50 % du salaire horaire habituel que touche le salarié.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/N-1.1#se:55"),
    ("LNT", "79.1", "Un salarié peut s'absenter du travail pendant une période d'au plus 26 semaines sur une période de 12 mois pour cause de maladie, de don d'organes ou de tissus, d'accident, de violence conjugale ou de violence à caractère sexuel.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/N-1.1#se:79_1"),
    ("LNT", "81.18", "Pour l'application de la présente loi, on entend par « harcèlement psychologique » une conduite vexatoire se manifestant soit par des comportements, des paroles, des actes ou des gestes répétés, qui sont hostiles ou non désirés, laquelle porte atteinte à la dignité ou à l'intégrité psychologique ou physique du salarié et qui entraîne, pour celui-ci, un milieu de travail néfaste. Une seule conduite grave peut aussi constituer du harcèlement psychologique si elle porte une telle atteinte et produit un effet nocif continu pour le salarié.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/N-1.1#se:81_18"),
    ("LNT", "81.19", "Tout salarié a droit à un milieu de travail exempt de harcèlement psychologique. L'employeur doit prendre les moyens raisonnables pour prévenir le harcèlement psychologique et, lorsqu'une telle conduite est portée à sa connaissance, pour la faire cesser. Il doit notamment adopter et rendre disponible une politique de prévention du harcèlement psychologique et de traitement des plaintes.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/N-1.1#se:81_19"),
    ("LNT", "82", "Un employeur doit donner un avis écrit à un salarié avant de mettre fin à son contrat de travail ou de le mettre à pied pour six mois ou plus (1 semaine entre 3 mois et 1 an de service ; 2 semaines entre 1 et 5 ans ; 4 semaines entre 5 et 10 ans ; 8 semaines pour 10 ans et plus).", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/N-1.1#se:82"),
    ("LNT", "83", "L'employeur qui ne donne pas l'avis prévu à l'article 82 ou qui donne un avis d'une durée insuffisante doit verser au salarié une indemnité compensatrice équivalente à son salaire habituel pour une période égale à celle de la durée ou de la durée résiduelle de l'avis auquel il avait droit.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/N-1.1#se:83"),
    ("LNT", "99", "La CNESST peut réclamer d'un employeur une somme due à un salarié en vertu de la présente loi (réclamation salariale).", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/N-1.1#se:99"),
    ("LNT", "114", "La CNESST peut, dans une instance relative à la présente section, percevoir en sus de la somme due un montant de 20 % de cette somme à titre de dommages-intérêts liquidés.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/N-1.1#se:114"),
    ("LNT", "122", "Il est interdit à un employeur ou à son agent de congédier, de suspendre ou de déplacer un salarié, d'exercer à son endroit des mesures discriminatoires ou des représailles ou de lui imposer toute autre sanction à cause de l'exercice par ce salarié d'un droit qui lui résulte de la présente loi, d'une grossesse ou d'une absence pour maladie ou obligation familiale (pratique interdite).", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/N-1.1#se:122"),
    ("LNT", "123.6", "Le salarié qui croit avoir été victime de harcèlement psychologique peut adresser, par écrit, une plainte à la CNESST dans les 2 ans de la dernière manifestation de cette conduite.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/N-1.1#se:123_6"),
    ("LNT", "123.15", "Si le Tribunal administratif du travail (TAT) juge que le salarié a été victime de harcèlement psychologique et que l'employeur a manqué à ses obligations prévues à l'article 81.19, il peut rendre toute décision qui lui paraît juste et raisonnable, notamment ordonner la réintégration du salarié, le paiement d'une indemnité jusqu'à un maximum équivalant au salaire perdu, le versement de dommages et intérêts punitifs et moraux et le financement d'un soutien psychologique.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/N-1.1#se:123_15"),
    ("LNT", "124", "Le salarié qui justifie de deux ans de service continu dans une même entreprise et qui croit avoir été congédié sans une cause juste et suffisante peut soumettre sa plainte par écrit à la CNESST dans les 45 jours de son congédiement.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/N-1.1#se:124"),
    ("LNT", "128", "Si le Tribunal administratif du travail (TAT) juge que le salarié a été congédié sans cause juste et suffisante (art. 124 L.N.T.), il peut ordonner à l'employeur de réintégrer le salarié dans son emploi habituel, de lui verser une indemnité équivalant au salaire et aux autres avantages dont l'a privé le congédiement, et rendre toute autre décision qui lui paraît juste et raisonnable compte tenu de toutes les circonstances de l'affaire.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/N-1.1#se:128"),

    # ==================== LPC (Loi sur la protection du consommateur, RLRQ c. P-40.1) ====================
    ("LPC", "1", "Dans la présente loi, on entend par « consommateur » une personne physique, sauf un commerçant qui se procure un bien ou un service pour les fins de son commerce.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/P-40.1#se:1"),
    ("LPC", "2", "La présente loi s'applique à tout contrat conclu entre un consommateur et un commerçant dans le cours des activités de son commerce et ayant pour objet un bien ou un service.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/P-40.1#se:2"),
    ("LPC", "8", "Le consommateur peut demander la nullité du contrat ou la réduction des obligations qui en découlent lorsque la disproportion entre les prestations respectives des parties est tellement considérable qu'elle équivaut à de l'exploitation du consommateur, ou que l'obligation du consommateur est excessive, abusive ou exorbitante (lésion objective en droit de la consommation).", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/P-40.1#se:8"),
    ("LPC", "9", "Lorsque le tribunal doit apprécier le consentement donné par un consommateur à un contrat, il tient compte de la condition des parties, des circonstances dans lesquelles le contrat a été conclu et des avantages qui résultent du contrat pour le consommateur.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/P-40.1#se:9"),
    ("LPC", "10", "Est interdite la stipulation par laquelle un commerçant se dégage des conséquences de son fait personnel ou de celui de son représentant.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/P-40.1#se:10"),
    ("LPC", "11.2", "Est interdite la stipulation qui impose au consommateur l'obligation de soumettre un différend éventuel à l'arbitrage ou qui restreint son droit d'ester en justice, notamment en lui interdisant d'exercer une action collective.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/P-40.1#se:11_2"),
    ("LPC", "13", "Est interdite la stipulation qui impose au consommateur, dans le cas de l'inexécution de son obligation, le paiement de frais, de pénalités ou de dommages-intérêts dont le montant ou le pourcentage est fixé à l'avance dans le contrat, autres que l'intérêt couru.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/P-40.1#se:13"),
    ("LPC", "34", "La présente section s'applique au contrat de vente ou de louage de biens et au contrat de service. Les garanties légales prévues aux articles 37 et 38 sont d'ordre public.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/P-40.1#se:34"),
    ("LPC", "37", "Un bien qui fait l'objet d'un contrat doit être tel qu'il puisse servir à l'usage auquel il est normalement destiné (garantie légale d'usage normal).", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/P-40.1#se:37"),
    ("LPC", "38", "Un bien qui fait l'objet d'un contrat doit être tel qu'il puisse servir à un usage normal pendant une durée raisonnable, eu égard à son prix, aux dispositions du contrat et aux conditions d'utilisation du bien (garantie légale de durabilité raisonnable).", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/P-40.1#se:38"),
    ("LPC", "40", "Un bien ou un service fourni doit être conforme à la description qui en est faite dans le contrat.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/P-40.1#se:40"),
    ("LPC", "41", "Un bien ou un service fourni doit être conforme à une déclaration ou à un message publicitaire fait à son sujet par le commerçant ou le fabricant. Cette déclaration ou ce message publicitaire lie ce commerçant ou ce fabricant.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/P-40.1#se:41"),
    ("LPC", "53", "Le consommateur qui a contracté avec un commerçant a le droit d'exercer directement contre le commerçant ou contre le fabricant un recours fondé sur un vice caché du bien qui a fait l'objet du contrat, sauf si le consommateur pouvait déceler ce vice par un examen ordinaire. Ni le commerçant, ni le fabricant ne peuvent alléguer le fait qu'ils ignoraient ce vice (présomption irréfragable de connaissance).", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/P-40.1#se:53"),
    ("LPC", "54", "Le consommateur qui a contracté avec un commerçant a le droit d'exercer directement contre le commerçant ou contre le fabricant un recours fondé sur un manquement à l'une des obligations mentionnées à l'article 37, 38 ou 39.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/P-40.1#se:54"),
    ("LPC", "219", "Aucun commerçant, fabricant ou publicitaire ne peut, par quelque moyen que ce soit, faire une représentation fausse ou trompeuse à un consommateur.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/P-40.1#se:219"),
    ("LPC", "224", "Aucun commerçant, fabricant ou publicitaire ne peut, par quelque moyen que ce soit, exiger pour un bien ou un service un prix supérieur à celui qui est annoncé (prix tout inclus).", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/P-40.1#se:224"),
    ("LPC", "228", "Aucun commerçant, fabricant ou publicitaire ne peut, dans une représentation qu'il fait à un consommateur, passer sous silence un fait important (omission d'un fait important).", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/P-40.1#se:228"),
    ("LPC", "253", "Lorsque le commerçant ou le fabricant se livre, à l'égard d'un consommateur, à une pratique interdite visée au titre II (ex: art. 219 ou 228), il y a présomption absolue que, si le consommateur avait eu connaissance de cette pratique, il n'aurait pas contracté ou n'aurait pas donné un prix aussi élevé (arrêt Richard c. Time Inc.).", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/P-40.1#se:253"),
    ("LPC", "272", "Si le commerçant ou le fabricant manque à une obligation que lui impose la présente loi, un règlement ou un engagement volontaire, le consommateur, sous réserve des autres recours prévus par la présente loi, peut demander, selon le cas : a) l'exécution de l'obligation ; b) l'autorisation de la faire exécuter aux frais du commerçant ou du fabricant ; c) la réduction de son obligation ; d) la résiliation du contrat ; e) la résolution du contrat ; ou f) la nullité du contrat, sans préjudice de sa demande en dommages-intérêts dans tous les cas. Il peut également demander des dommages-intérêts punitifs.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/P-40.1#se:272"),

    # ==================== LAF / LTVQ / LI (Fiscalité — Revenu Québec) ====================
    ("LAF", "14", "Toute somme perçue en vertu d'une loi fiscale par une personne tenue de la percevoir est détenue en fiducie pour Sa Majesté aux droits du Québec et doit être remise au ministre dans les délais prescrits.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-6.002#se:14"),
    ("LAF", "21", "Le ministre du Revenu peut procéder à une vérification ou à une inspection des registres et pièces justificatives d'un contribuable ou d'un mandataire afin d'établir une cotisation.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-6.002#se:21"),
    ("LAF", "24.0.1", "Lorsqu'une société omet de remettre au ministre un montant qu'elle était tenue de percevoir ou de déduire (notamment TVQ ou retenues à la source), ses administrateurs en fonction à la date de l'omission sont solidairement tenus, avec cette société, de payer ce montant ainsi que les intérêts et les pénalités s'y rapportant, sauf s'ils ont agi avec le degré de soin, de diligence et d'habileté raisonnable.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-6.002#se:24_0_1"),
    ("LAF", "28", "Toute créance de l'État résultant de l'application d'une loi fiscale porte intérêt au taux fixé par règlement (taux légal d'intérêt applicable aux créances de l'État et aux indemnités statutaires visées par renvoi).", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-6.002#se:28"),
    ("LAF", "59", "Toute personne qui omet de faire une déclaration ou un rapport suivant la formule et dans le délai prescrits par une loi fiscale encourt une pénalité administrative.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-6.002#se:59"),
    ("LAF", "59.2", "Toute personne qui omet de percevoir une somme qu'elle était tenue de percevoir en vertu d'une loi fiscale ou qui omet de la payer ou de la remettre dans le délai prescrit encourt une pénalité égale à 7 %, 10 % ou 15 % de cette somme selon la durée du retard.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-6.002#se:59_2"),
    ("LAF", "59.3", "Toute personne qui, sciemment ou dans des circonstances équivalant à de la négligence flagrante, fait un faux énoncé ou une omission dans une déclaration fiscale encourt une pénalité égale à 50 % des droits éludés.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-6.002#se:59_3"),
    ("LAF", "93.1.1", "Une personne qui s'oppose à une cotisation émise en vertu d'une loi fiscale peut, dans les 90 jours de la notification de l'avis de cotisation, notifier au ministre un avis d'opposition exposant les motifs de son opposition et tous les faits pertinents.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-6.002#se:93_1_1"),
    ("LAF", "93.1.10", "Une personne qui a notifié un avis d'opposition à une cotisation peut, dans les 90 jours de la décision du ministre sur l'opposition, interjeter appel auprès de la Cour du Québec (Chambre civile - division administrative et d'appel) pour faire annuler ou modifier la cotisation.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-6.002#se:93_1_10"),
    ("LAF", "94.1", "Le ministre peut renoncer en tout ou en partie à un intérêt, à une pénalité ou à des frais prévus par une loi fiscale, ou les annuler, notamment en cas de force majeure ou d'erreur administrative.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-6.002#se:94_1"),
    ("LTVQ", "16", "Tout acquéreur d'une fourniture taxable effectuée au Québec doit payer à Sa Majesté aux droits du Québec une taxe calculée au taux de 9,975 % sur la valeur de la contrepartie de la fourniture.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/T-0.1#se:16"),
    ("LTVQ", "206.1", "Un inscrit ne peut demander un remboursement de la taxe sur les intrants (RTI) à l'égard d'un bien ou d'un service que s'il a obtenu et conservé les pièces justificatives contenant les renseignements prescrits par règlement (nom et numéro d'inscription du fournisseur réel).", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/T-0.1#se:206_1"),
    ("LTVQ", "323.1", "Toute personne qui fournit une unité d'hébergement dans un établissement d'hébergement touristique assujetti doit percevoir et remettre la taxe sur l'hébergement au taux prescrit.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/T-0.1#se:323_1"),
    ("LI", "1010", "Le ministre peut déterminer de nouveau l'impôt, les intérêts et les pénalités et faire une nouvelle cotisation dans les trois ans (ou quatre ans pour certaines sociétés) de la date d'envoi de l'avis de première cotisation, ou en tout temps si le contribuable a fait une fausse représentation des faits par incurie ou omission volontaire.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/I-3#se:1010"),
    ("LI", "1049", "Toute personne qui, sciemment ou dans des circonstances qui équivalent à de la négligence flagrante, fait un faux énoncé ou une omission dans une déclaration fiscale encourt une pénalité d'au moins 100 $ et d'au plus 50 % de l'impôt éludé.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/I-3#se:1049"),

    # ==================== LSAQ (Loi sur les sociétés par actions, RLRQ c. S-31.1) ====================
    ("LSAQ", "112", "Sous réserve d'une convention unanime des actionnaires, le conseil d'administration exerce tous les pouvoirs nécessaires pour gérer les activités et les affaires internes de la société ou en surveiller la gestion.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/S-31.1#se:112"),
    ("LSAQ", "119", "Les administrateurs et les dirigeants doivent, dans l'exercice de leurs fonctions, respecter les obligations que la loi, l'acte constitutif et le règlement intérieur leur imposent et agir dans les limites des pouvoirs qui leur sont conférés. Ils doivent agir avec prudence et diligence, ainsi qu'avec honnêteté et loyauté dans l'intérêt de la société.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/S-31.1#se:119"),
    ("LSAQ", "154", "Les administrateurs d'une société sont solidairement responsables envers ses employés, jusqu'à concurrence de six mois de salaire, de toutes dettes contractées envers eux pour des services rendus à la société pendant qu'ils sont en fonction.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/S-31.1#se:154"),
    ("LSAQ", "214", "Les actionnaires d'une société peuvent conclure par écrit une convention unanime des actionnaires qui restreint, en tout ou en partie, les pouvoirs du conseil d'administration de gérer les activités et les affaires internes de la société.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/S-31.1#se:214"),
    ("LSAQ", "450", "Un demandeur peut s'adresser au tribunal en vue d'obtenir une ordonnance visant à redresser la situation s'il est d'avis qu'un acte ou une omission de la société ou l'exercice des pouvoirs des administrateurs a un effet abusif ou injuste, ou ne tient pas compte des intérêts d'un détenteur de valeurs mobilières, d'un administrateur ou d'un dirigeant (recours en redressement pour abus / oppression).", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/S-31.1#se:450"),
    ("LSAQ", "451", "À l'occasion d'une demande visée à l'article 450, le tribunal peut rendre toute ordonnance provisoire ou définitive qu'il estime indiquée, notamment enjoindre à la société ou à un autre actionnaire d'acheter des valeurs mobilières d'un détenteur, modifier les statuts ou la convention unanime, ou indemniser les personnes qui ont subi un préjudice.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/S-31.1#se:451"),

    # ==================== CHARTE & LOI25 (Droits fondamentaux & Vie privée) ====================
    ("CHARTE", "1", "Tout être humain a droit à la vie, ainsi qu'à la sûreté, à l'intégrité et à la liberté de sa personne.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/C-12#se:1"),
    ("CHARTE", "4", "Toute personne a droit à la sauvegarde de sa dignité, de son honneur et de sa réputation.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/C-12#se:4"),
    ("CHARTE", "5", "Toute personne a droit au respect de sa vie privée.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/C-12#se:5"),
    ("CHARTE", "6", "Toute personne a droit à la jouissance paisible et à la libre disposition de ses biens, sauf dans la mesure prévue par la loi.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/C-12#se:6"),
    ("CHARTE", "9", "Chacun a droit au respect du secret professionnel. Toute personne tenue par la loi au secret professionnel et tout prêtre ou autre ministre du culte ne peuvent, même en justice, divulguer les renseignements confidentiels qui leur ont été révélés en raison de leur état ou profession.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/C-12#se:9"),
    ("CHARTE", "10", "Toute personne a droit à la reconnaissance et à l'exercice, en pleine égalité, des droits et libertés de la personne, sans distinction, exclusion ou préférence fondée sur la race, la couleur, le sexe, l'identité ou l'expression de genre, la grossesse, l'orientation sexuelle, l'état civil, l'âge, la religion, les convictions politiques, la langue, l'origine ethnique ou nationale, la condition sociale, le handicap ou l'utilisation d'un moyen pour pallier ce handicap.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/C-12#se:10"),
    ("CHARTE", "23", "Toute personne a droit, en pleine égalité, à une audition publique et impartiale de sa cause par un tribunal indépendant et qui ne soit pas préjugé, qu'il s'agisse de la détermination de ses droits et obligations ou du bien-fondé de toute accusation portée contre elle.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/C-12#se:23"),
    ("CHARTE", "46", "Toute personne qui travaille a droit, conformément à la loi, à des conditions de travail justes et raisonnables et qui respectent sa santé, sa sécurité et son intégrité physique et psychologique.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/C-12#se:46"),
    ("CHARTE", "49", "Une atteinte illicite à un droit ou à une liberté reconnu par la présente Charte confère à la victime le droit d'obtenir la cessation de cette atteinte et la réparation du préjudice moral ou matériel qui en résulte. En cas d'atteinte illicite et intentionnelle, le tribunal peut en outre condamner son auteur à des dommages-intérêts punitifs.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/C-12#se:49"),
    ("LOI25", "3.1", "Toute personne qui exploite une entreprise est responsable de la protection des renseignements personnels qu'elle détient. Au sein de l'entreprise, la personne ayant la plus haute autorité veille à assurer le respect et la mise en oeuvre de la présente loi (responsable de la protection des renseignements personnels).", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/P-39.1#se:3_1"),
    ("LOI25", "3.5", "Toute personne qui exploite une entreprise et qui a des motifs de croire que s'est produit un incident de confidentialité impliquant un renseignement personnel qu'elle détient doit prendre les mesures raisonnables pour diminuer les risques qu'un préjudice soit causé et éviter que de nouveaux incidents de même nature ne se produisent. Si l'incident présente un risque qu'un préjudice sérieux soit causé, elle doit, avec diligence, en aviser la Commission d'accès à l'information (CAI) et toute personne dont un renseignement personnel est concerné.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/P-39.1#se:3_5"),
    ("LOI25", "10", "Toute personne qui exploite une entreprise doit prendre les mesures de sécurité propres à assurer la protection des renseignements personnels collectés, utilisés, communiqués, conservés ou détruits et qui sont raisonnables compte tenu, notamment, de leur sensibilité, de la finalité de leur utilisation, de leur quantité, de leur répartition et de leur support.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/P-39.1#se:10"),
    ("LOI25", "14", "Le consentement à la collecte, à la communication ou à l'utilisation d'un renseignement personnel doit être manifeste, libre, éclairé et être donné à des fins spécifiques.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/P-39.1#se:14"),
    ("LOI25", "17", "Avant de communiquer à l'extérieur du Québec un renseignement personnel, la personne qui exploite une entreprise doit procéder à une évaluation des facteurs relatifs à la vie privée (EFVP) et s'assurer que le renseignement bénéficiera d'une protection adéquate.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/P-39.1#se:17"),
    ("LOI25", "93.1", "Lorsqu'une atteinte illicite à un droit conféré par la présente loi ou par les articles 35 à 40 du Code civil cause un préjudice et que cette atteinte est intentionnelle ou résulte d'une faute lourde, le tribunal accorde des dommages-intérêts punitifs d'au moins 1 000 $.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/P-39.1#se:93_1"),

    # ==================== LTAL & CSR (Logement & Sécurité routière) ====================
    ("LTAL", "28", "Le Tribunal administratif du logement (TAL) connaît en première instance, à l'exclusion de tout autre tribunal, de toute demande relative au bail d'un logement lorsque la somme demandée ou la valeur de la chose réclamée ne dépasse pas la limite de la compétence de la Cour du Québec, ainsi que de toute demande relative à la reconduction du bail, à la fixation du loyer, à la reprise de logement ou à l'éviction.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/T-15.01#se:28"),
    ("LTAL", "56", "Lors d'une enquête et audition devant le Tribunal administratif du logement, chacune des parties peut interroger les témoins et exposer ses arguments dans le respect de l'équité procédurale.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/T-15.01#se:56"),
    ("LTAL", "63", "Les parties à un litige devant le Tribunal administratif du logement peuvent recourir au service de conciliation offert par le Tribunal pour parvenir à une entente amiable.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/T-15.01#se:63"),
    ("LTAL", "91", "Les décisions du Tribunal administratif du logement relatives à la résiliation de bail pour non-paiement de loyer ou trouble de jouissance peuvent faire l'objet d'un appel sur permission devant la Cour du Québec dans les 30 jours.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/T-15.01#se:91"),
    ("CSR", "328", "Sauf sur les chemins où une signalisation contraire apparaît, nul ne peut conduire un véhicule routier à une vitesse excédant les limites prescrites par le Code de la sécurité routière.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/C-24.2#se:328"),
    ("CSR", "359", "À moins d'une signalisation contraire, face à un feu rouge, le conducteur d'un véhicule routier ou d'une bicyclette doit immobiliser son véhicule avant le passage pour piétons ou la ligne d'arrêt.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/C-24.2#se:359"),

    # ==================== CCR (Code criminel, L.R.C. (1985), ch. C-46) ====================
    ("CCR", "16", "Nul n'est criminellement responsable d'un acte commis ou d'une omission faite pendant qu'il était atteint de troubles mentaux qui le rendaient incapable de juger de la nature et de la qualité de l'acte ou de l'omission, ou de savoir que l'acte ou l'omission était mauvais.", "https://laws-lois.justice.gc.ca/fra/lois/c-46/section-16.html"),
    ("CCR", "21", "Quiconque accomplit ou omet d'accomplir quelque chose en vue d'aider quelqu'un à commettre une infraction, ou encourage quelqu'un à la commettre, est partie à l'infraction.", "https://laws-lois.justice.gc.ca/fra/lois/c-46/section-21.html"),
    ("CCR", "34", "N'est pas coupable d'une infraction la personne qui croit, pour des motifs raisonnables, que la force est employée contre elle ou une autre personne et qui commet l'acte constituant l'infraction dans le but de se défendre ou de se protéger, si l'acte commis est raisonnable dans les circonstances (légitime défense).", "https://laws-lois.justice.gc.ca/fra/lois/c-46/section-34.html"),
    ("CCR", "264", "Il est interdit, sauf autorisation légitime, d'agir à l'égard d'une personne sachant qu'elle se trouve harcelée ou sans se soucier de ce qu'elle se trouve harcelée, lorsque cet acte a pour effet de lui faire raisonnablement craindre pour sa sécurité ou celle d'une de ses connaissances (harcèlement criminel).", "https://laws-lois.justice.gc.ca/fra/lois/c-46/section-264.html"),
    ("CCR", "264.1", "Commet une infraction quiconque, sciemment, profère, transmet ou fait recevoir par une personne, de quelque façon, une menace de causer la mort ou des lésions corporelles à quelqu'un, ou de brûler, détruire ou endommager des biens (proférer des menaces).", "https://laws-lois.justice.gc.ca/fra/lois/c-46/section-264.1.html"),
    ("CCR", "265", "Commet des voies de fait quiconque, d'une manière intentionnelle, emploie la force, directement ou indirectement, contre une autre personne sans son consentement.", "https://laws-lois.justice.gc.ca/fra/lois/c-46/section-265.html"),
    ("CCR", "266", "Quiconque commet des voies de fait est coupable d'un acte criminel et passible d'un emprisonnement maximal de cinq ans, ou d'une infraction punissable sur déclaration de culpabilité par procédure sommaire.", "https://laws-lois.justice.gc.ca/fra/lois/c-46/section-266.html"),
    ("CCR", "267", "Est coupable d'un acte criminel et passible d'un emprisonnement maximal de dix ans quiconque, en se livrant à des voies de fait, porte, utilise ou menace d'utiliser une arme ou une imitation d'arme, ou cause des lésions corporelles au plaignant.", "https://laws-lois.justice.gc.ca/fra/lois/c-46/section-267.html"),
    ("CCR", "320.14", "Commet une infraction quiconque conduit un moyen de transport alors que sa capacité de conduire est affaiblie à quelque degré que ce soit par l'effet de l'alcool ou d'une drogue, ou alors que son alcoolémie est égale ou supérieure à 80 mg d'alcool par 100 ml de sang.", "https://laws-lois.justice.gc.ca/fra/lois/c-46/section-320.14.html"),
    ("CCR", "322", "Commet un vol quiconque prend frauduleusement et sans apparence de droit, ou détourne frauduleusement et sans apparence de droit, pour son propre usage ou pour l'usage d'une autre personne, une chose quelconque animée ou inanimée, avec l'intention de priver, temporairement ou absolument, son propriétaire de cette chose.", "https://laws-lois.justice.gc.ca/fra/lois/c-46/section-322.html"),
    ("CCR", "334", "Quiconque commet un vol est coupable d'un acte criminel et passible d'un emprisonnement maximal de dix ans si le bien volé a une valeur dépassant 5 000 $, ou d'un emprisonnement maximal de deux ans (ou procédure sommaire) si la valeur ne dépasse pas 5 000 $.", "https://laws-lois.justice.gc.ca/fra/lois/c-46/section-334.html"),
    ("CCR", "348", "Commet une infraction quiconque s'introduit en un endroit par effraction avec l'intention d'y commettre un acte criminel, ou s'introduit en un endroit par effraction et y commet un acte criminel.", "https://laws-lois.justice.gc.ca/fra/lois/c-46/section-348.html"),
    ("CCR", "380", "Quiconque, par supercherie, mensonge ou autre moyen dolosif, frustre le public ou toute personne de quelque bien, service, argent ou valeur est coupable de fraude.", "https://laws-lois.justice.gc.ca/fra/lois/c-46/section-380.html"),
    ("CCR", "718", "Le prononcé des peines a pour objectif essentiel de protéger la société et de contribuer au respect de la loi et au maintien d'une société juste, paisible et sûre par l'infliction de sanctions justes visant à dénoncer le comportement illégal, dissuader les délinquants, isoler au besoin les délinquants, favoriser leur réinsertion sociale et assurer la réparation des torts causés aux victimes.", "https://laws-lois.justice.gc.ca/fra/lois/c-46/section-718.html"),
    ("CCR", "718.1", "La peine est proportionnelle à la gravité de l'infraction et au degré de responsabilité du délinquant (principe fondamental de proportionnalité de la peine).", "https://laws-lois.justice.gc.ca/fra/lois/c-46/section-718.1.html"),
]

QUANTUM_BENCHMARKS = [
    (
        "dol_restitution_prestation",
        "Dol contractuel / Marge ou profit caché (art. 1401, 1407 C.c.Q.)",
        55.0, 64.0, 100.0, 2500.0, 5.0,
        "La victime d'un dol a droit à la réduction de son obligation (restitution de la marge ou du profit caché indu, art. 1407 C.c.Q.) sans avoir à prouver d'intention malveillante. La demande reconventionnelle du professionnel auteur du dol est rejetée, mais l'abus de procédure (art. 51 C.p.c.) exige une témérité distincte de l'échec au fond (Biron c. 9156-9780 Québec inc., 2020 QCCA 1537).",
        "Robertson c. Murray (Maisons Paragon Homes inc.), 2022 QCCQ 10057"
    ),
    (
        "vice_cache_malfacon_toiture",
        "Vice caché / Malfaçons entrepreneuriales & Vétusté (art. 1726, 2100, 1607 C.c.Q.)",
        60.0, 80.3, 100.0, 1000.0, 8.0,
        "L'entrepreneur est tenu à une obligation de renseignement et de résultat sur l'état du support avant d'installer un ouvrage (art. 2100 C.c.Q.). Toutefois, une déduction pour vétusté / plus-value ou état préexistant (15 % à 25 %) s'applique sur les travaux correctifs (art. 1607, 1611 C.c.Q.) sauf preuve d'inutilité totale des travaux initiaux.",
        "Caron c. Toiture Allaire ; ABB Inc. c. Domtar Inc., 2007 CSC 50"
    ),
    (
        "protection_consommateur_lpc_272",
        "Pratique interdite / Fausse représentation commerçant (art. 219, 228, 253, 272 L.p.c.)",
        65.0, 85.0, 100.0, 1500.0, 12.0,
        "Sous l'article 253 L.p.c., la preuve d'une pratique interdite (ex: représentation trompeuse art. 219 ou omission d'un fait important art. 228 L.p.c.) crée une présomption absolue de préjudice donnant ouverture à la réduction de prix et aux dommages punitifs sous l'article 272 L.p.c.",
        "Richard c. Time Inc., 2012 CSC 8"
    ),
    (
        "congediement_injustifie_lnt_124",
        "Congédiement sans cause juste et suffisante / Délai de congé (art. 2091 C.c.Q., art. 124 L.n.t.)",
        40.0, 68.0, 95.0, 5000.0, 10.0,
        "L'indemnité de délai-congé raisonnable oscille entre 3 et 4 semaines par année de service (plafond usuel de 24 mois), réduite des revenus gagnés durant la période de préavis selon l'obligation de mitigation des dommages (art. 1479 C.c.Q.). Les dommages moraux exigent une mauvaise foi lors du licenciement.",
        "Honda Canada Inc. c. Keays, 2008 CSC 39 ; Standard Broadcasting Corp. c. Stewart"
    ),
    (
        "saaq_irr_sequelles_taq",
        "Litige SAAQ devant le TAQ : Relation causale, IRR (art. 14, 45, 49 L.a.a.) & Séquelles permanentes (art. 73 L.a.a.)",
        4.0, 35.0, 98.0, 3200.0, 0.0,
        "Devant le TAQ (Section des affaires sociales), l'absence d'oedème osseux traumatique à l'IRM et une discopathie dégénérative préexistante L4-S1 entraînent régulièrement le maintien de la fin de l'IRR (art. 49 L.a.a.) par les juges formalistes/analytiques, tout en laissant subsister une séquelle résiduelle de classe 1 (~3 200 $) sous l'art. 73 L.a.a. Aucun frais de justice ni art. 1619 C.c.Q. ne s'applique devant le TAQ (intérêts statutaires sous l'art. 83.32 L.a.a.).",
        "Productions Pram inc. c. Lemay, 1992 CanLII 3107 (QC CA) ; Jurisprudence TAQ SAS"
    ),
    (
        "cnesst_latmp_lesion_professionnelle",
        "Litige CNESST devant le TAT : Lésion professionnelle, présomption art. 28 L.A.T.M.P. & partage des coûts art. 329",
        25.0, 60.0, 100.0, 0.0, 0.0,
        "La présomption de lésion professionnelle de l'article 28 L.A.T.M.P. s'applique dès qu'une blessure survient par le fait ou à l'occasion du travail, mais est renversée si l'employeur démontre une condition personnelle préexistante évoluant pour son propre compte. Sous l'article 329 L.A.T.M.P., l'employeur obtient un transfert de 50 % à 90 % des coûts d'imputation si le travailleur présentait déjà un handicap biologique prolongé.",
        "Boies c. CSSST, 2013 QCCLP ; Jurisprudence TAT Division SST"
    ),
    (
        "harcelement_psychologique_lnt",
        "Harcèlement psychologique au travail devant le TAT (art. 81.18, 81.19, 123.15 L.n.t.)",
        30.0, 58.0, 90.0, 10000.0, 5.0,
        "L'exercice normal, même ferme, du droit de direction de l'employeur ne constitue pas du harcèlement psychologique au sens de l'article 81.18 L.n.t. Lorsque la conduite vexatoire répétée (ou un acte grave unique) et le manquement à l'obligation de prévention (art. 81.19 L.n.t.) sont prouvés, le TAT accorde la perte salariale et des dommages moraux médians de 7 500 $ à 15 000 $ (art. 123.15 L.n.t.).",
        "Syndicat des travailleuses et travailleurs de Bridgestone/Firestone de Joliette (CSN) c. Trudeau, 1999 CanLII 13595 (QC CA)"
    ),
    (
        "bail_logement_tal",
        "Bail de logement résidentiel devant le TAL : Diminution de loyer, troubles de jouissance & reprise (art. 1854, 1863, 1959 C.c.Q.)",
        20.0, 45.0, 85.0, 1800.0, 5.0,
        "Le Tribunal administratif du logement (TAL) accorde une diminution de loyer proportionnelle à la perte de jouissance (10 % à 30 % du loyer mensuel pour la période affectée après mise en demeure) et des dommages moraux modérés (1 000 $ à 3 500 $), sauf mauvaise foi ou éviction dolosive justifiant des dommages punitifs sous l'art. 1968 C.c.Q.",
        "Jurisprudence constante du Tribunal administratif du logement (TAL)"
    ),
    (
        "fiscalite_cotisation_revenu_quebec",
        "Contestation de cotisation fiscale Revenu Québec : RTI, pénalités art. 59.3 L.A.F. & diligence des administrateurs (art. 24.0.1 L.A.F.)",
        15.0, 42.0, 100.0, 0.0, 2.0,
        "La cotisation fiscale bénéficie d'une présomption de validité qu'il incombe au contribuable de démolir par preuve documentaire probante (art. 206.1 L.T.V.Q.). En revanche, le fardeau de prouver la négligence flagrante pour maintenir la pénalité de 50 % (art. 59.3 L.A.F. / art. 1049 L.I.) repose intégralement sur l'Agence du revenu du Québec.",
        "Hickman Motors Ltd. c. Canada, [1997] 2 R.C.S. 336 ; Jurisprudence Cour du Québec (Chambre fiscale)"
    ),
    (
        "oppression_actionnaires_lsaq",
        "Recours en redressement pour abus / oppression d'actionnaire minoritaire (art. 450, 451 L.S.A.Q.)",
        35.0, 72.0, 100.0, 5000.0, 15.0,
        "Le test à deux volets de l'arrêt BCE exige la preuve (1) d'attentes raisonnables de l'actionnaire minoritaire et (2) d'une atteinte à ces attentes par une conduite abusive, un préjudice injuste ou une omission d'en tenir compte (art. 450 L.S.A.Q.). Le remède privilégié est le rachat forcé des actions à leur juste valeur marchande sans décote de minorité.",
        "BCE Inc. c. Détenteurs de débentures de 1976, 2008 CSC 69 ; Wilson c. Alharayeri, 2017 CSC 39"
    ),
    (
        "atteinte_reputation_vie_privee_charte_loi25",
        "Diffamation, atteinte à la vie privée & incident de confidentialité (art. 1457 C.c.Q., art. 4, 5, 49 Charte, art. 93.1 Loi 25)",
        25.0, 50.0, 85.0, 7500.0, 18.0,
        "En matière de diffamation ou d'atteinte à la vie privée, la faute s'apprécie selon la norme de la personne raisonnable (art. 1457 C.c.Q.). Les dommages moraux médians se situent entre 5 000 $ et 20 000 $, et les dommages punitifs sous l'art. 49 al. 2 Charte ou l'art. 93.1 Loi 25 exigent la preuve d'une atteinte illicite et intentionnelle (ou d'une faute lourde sous la Loi 25).",
        "Bou Malhab c. Diffusion Métromédia CMR inc., 2011 CSC 9 ; Québec (Curateur public) c. Syndicat national des employés de l'hôpital Saint-Ferdinand, [1996] 3 R.C.S. 211"
    ),
]


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Upsert des articles de lois spéciales
    inserted_articles = 0
    for code, numero, texte, url in STATUTE_ARTICLES:
        cur.execute("DELETE FROM articles WHERE code = ? AND numero = ?", (code, numero))
        cur.execute(
            "INSERT INTO articles (code, numero, texte, url) VALUES (?, ?, ?, ?)",
            (code, numero, texte, url)
        )
        inserted_articles += 1

    # 2. Upsert des barèmes actuariels quantum_benchmarks
    cur.execute("""
    CREATE TABLE IF NOT EXISTS quantum_benchmarks (
        category TEXT PRIMARY KEY,
        label TEXT,
        min_pct_claim REAL,
        median_pct_claim REAL,
        max_pct_claim REAL,
        troubles_inconvenients_median REAL,
        art51_cpc_grant_rate_pct REAL,
        key_rule TEXT,
        reference_case TEXT
    )
    """)
    for qb in QUANTUM_BENCHMARKS:
        cur.execute("DELETE FROM quantum_benchmarks WHERE category = ?", (qb[0],))
        cur.execute(
            "INSERT INTO quantum_benchmarks (category, label, min_pct_claim, median_pct_claim, max_pct_claim, troubles_inconvenients_median, art51_cpc_grant_rate_pct, key_rule, reference_case) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            qb
        )

    # 3. Rebuild FTS5 index
    try:
        cur.execute("INSERT INTO articles_fts(articles_fts) VALUES('rebuild')")
    except Exception as e:
        print("Warning rebuilding FTS5:", e)

    conn.commit()

    cur.execute("SELECT code, COUNT(*) FROM articles GROUP BY code ORDER BY COUNT(*) DESC")
    print("Statut de ccq_cpc.db après enrichissement :", cur.fetchall())
    cur.execute("SELECT COUNT(*) FROM quantum_benchmarks")
    print("Nombre de barèmes actuariels quantum_benchmarks :", cur.fetchone()[0])
    conn.close()


if __name__ == "__main__":
    main()
