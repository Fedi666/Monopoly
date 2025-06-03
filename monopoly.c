#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <windows.h>
#include <mmsystem.h>
#define JAIL_POSITION 10
#define JAIL_FINE 50
#define JAIL_PENALTY 5
#define START_BONUS 200
#define MAX_JOUEURS 8
#define NUM_CASES 40
#define MAX_LINE_LENGTH 100
#define NUM_CARTE_CAISSE 14
#define NUM_CARTE_CHANCE 13
#define GAIN 1700
typedef struct {
    int id;
    char name[50];
    char type[20];
    int price;
    int rent;
    int owner;
} Case;

typedef struct {
    Case cases[NUM_CASES];
} Board;

typedef struct {
    int id;
    char nom[50];
    int argent;
    int nbtour;
    int position;
    int enPrison;
    int nbpropriete;
    int proprietes[28];
    int maisons;
    int hotels;
} Joueur;

typedef struct {
    Case cases;
    int nbmaisons;
    int nbhotels;
    float prixmaison;
    float prixhotels;
} Propriete;
typedef struct {
	int id;
	char description[MAX_LINE_LENGTH];
} Carte;
Carte cartecaisse[NUM_CARTE_CAISSE];
typedef struct {
    int id;
    char description[256];
    char actionType[50];
    int montant;
    int position;
} CarteChance;
Carte cartechance[NUM_CARTE_CAISSE];

void loadBoardFromFile(Board *board, const char *filename) {
    FILE *file = fopen(filename, "r");
    if (file == NULL) {
        printf("Erreur : Impossible d'ouvrir le fichier %s.\n", filename);
        exit(1);
    }

    char line[MAX_LINE_LENGTH];
    int index = 0;

    while (fgets(line, sizeof(line), file) && index < NUM_CASES) {
        sscanf(line, "%d,%49[^,],%19[^,],%d,%d,%d",
               &board->cases[index].id,
               board->cases[index].name,
               board->cases[index].type,
               &board->cases[index].price,
               &board->cases[index].rent,
               &board->cases[index].owner);
        index++;
    }

    fclose(file);
}



    void loadCarteChanceFromFile(const char *filename) {
    FILE *file = fopen(filename, "r");
    if (file == NULL) {
        printf("Erreur : Impossible de charger le fichier des cartes Chance.\n");
        exit(1);
    }

    char line[MAX_LINE_LENGTH];
    int index = 0;

    while (fgets(line, sizeof(line), file) && index < NUM_CARTE_CHANCE) {
        sscanf(line, "%d,%99[^\n]", &cartechance[index].id, cartechance[index].description);
        index++;
    }

    fclose(file);
}




void displayBoard(Board *board) {
    printf("### Informations du Plateau ###\n");
    int i;
    for (i = 0; i < NUM_CASES; i++) {
        printf("Case %d: %s [%s] - Prix: %d, Loyer: %d, Propriétaire: %d\n",
               board->cases[i].id,
               board->cases[i].name,
               board->cases[i].type,
               board->cases[i].price,
               board->cases[i].rent,
               board->cases[i].owner);
    }
}
void loadCarteCaisseFromFile(const char *filename){
	FILE *file = fopen(filename,"r");
	if(file==NULL){
		printf("erreur lors de chargement de fichier \n ");
		exit (1);
	}
	char line[MAX_LINE_LENGTH];
    int index = 0;

    while (fgets(line, sizeof(line), file) && index < NUM_CARTE_CAISSE) {
        sscanf(line, "%d,%99[^\n]", &cartecaisse[index].id, cartecaisse[index].description);
        index++;
    }

    fclose(file);
}

void initialiserJoueurs(Joueur joueurs[], int *nbJoueurs) {
    printf("Entrez le nombre de joueurs (2 à %d) : ", MAX_JOUEURS);
    scanf("%d", nbJoueurs);

    while (*nbJoueurs < 2 || *nbJoueurs > MAX_JOUEURS) {
        printf("Nombre invalide. Entrez un nombre entre 2 et %d : ", MAX_JOUEURS);
        scanf("%d", nbJoueurs);
    }
   int i;
    for ( i = 0; i < *nbJoueurs; i++) {
        printf("Entrez le nom du joueur %d : ", i + 1);
        scanf("%s", joueurs[i].nom);
        joueurs[i].argent = 1500;
        joueurs[i].position = 0;
        joueurs[i].nbtour = 0;
        joueurs[i].nbpropriete=0;
        joueurs[i].enPrison = 0;
        joueurs[i].maisons = 0;
        joueurs[i].hotels = 0;
       int j;
        for ( j = 0; j < 28; j++) {
            joueurs[i].proprietes[j] = -1;
        }

        printf("Joueur %s initialisé avec %d unités d'argent.\n", joueurs[i].nom, joueurs[i].argent);
    }
}

void displayJoueurs(Joueur *joueur, int nbjoueur) {
	int i;
    for ( i = 0; i < nbjoueur; i++) {
        printf("Le joueur: %s, à la position: %d, a %d unités d'argent, et possède %d propriété(s)\n",
               joueur[i].nom, joueur[i].position, joueur[i].argent, joueur[i].nbpropriete);
    }
}

int calculerLoyer(Propriete *p) {
    int loyer = p->cases.rent;
    if (p->cases.owner != -1) {
        loyer += (int)(p->cases.rent * (p->nbhotels * 0.8)) + (int)(p->cases.rent * (p->nbmaisons * 0.5));
    }
    return loyer;
}

bool acheterPropriete(Propriete *p, Joueur *j) {
    if (j->nbtour == 0) {
        printf("Vous n'avez pas le droit d'acheter cette propriété.\n");
        return false;
    }

    if (p->cases.owner != -1) {
        printf("La propriété %s est déjà achetée par un autre joueur.\n", p->cases.name);
        return false;
    }

    if (j->argent < p->cases.price) {
        printf("Le joueur %s n'a pas assez d'argent.\n", j->nom);
        return false;
    }

    j->argent -= p->cases.price;
    p->cases.owner = j->id;
    printf("Félicitations ! Le joueur %s a acheté %s. Il vous reste %d.\n", j->nom, p->cases.name, j->argent);

    if (j->nbpropriete < 28) {
        j->nbpropriete++;
    } else {
        printf("Le joueur %s ne peut pas posséder plus de 28 propriétés.\n", j->nom);
    }

    return true;
}

bool payerloyer(Propriete *p, Joueur *j) {
    if (p->cases.owner == -1 || p->cases.owner == j->id) {
        printf("Cette propriété ne nécessite pas un paiement.\n");
        return false;
    }

    if (p->cases.rent > j->argent) {
        printf("Le joueur %s n'a pas assez d'argent.\n", j->nom);
        return false;
    } else {
    	int loyer;
    	loyer=calculerLoyer(p);
        j->argent -= loyer;
        printf("Le joueur %s a payé un loyer de %d.\n", j->nom, loyer);
        return true;
    }
}

bool achetermaison(Propriete *p, Joueur *j, int nb) {
    if (p->cases.owner != j->id) {
        printf("Vous n'avez pas le droit d'acheter cette propriété.\n");
        return false;
    }

    if (p->nbmaisons == 4 || p->nbmaisons + nb > 4) {
        printf("Vous ne pouvez pas avoir plus de 4 maisons pour une même propriété.\n");
        return false;
    }

    int prix = p->prixmaison * nb;
    if (j->argent < prix) {
        printf("Le joueur %s n'a pas assez d'argent.\n", j->nom);
        return false;
    }

    j->argent -= prix;
    p->nbmaisons += nb;
    j->maisons += nb;
    printf("Le joueur %s a acheté %d maison(s) sur %s. Il vous reste %d.\n", j->nom, nb, p->cases.name, j->argent);

    return true;
}

bool acheterhotel(Propriete *p, Joueur *j, int nb) {
    if (p->cases.owner != j->id) {
        printf("Vous n'avez pas le droit d'acheter cette propriété.\n");
        return false;
    }

    if (p->nbmaisons < 4) {
        printf("Vous devez d'abord avoir 4 maisons avant d'acheter un hôtel.\n");
        return false;
    }

    if (p->nbhotels == 4 || p->nbhotels + nb > 4) {
        printf("Vous ne pouvez pas avoir plus de 4 hôtels pour une même propriété.\n");
        return false;
    }

    int prix = p->prixhotels * nb;
    if (j->argent < prix) {
        printf("Le joueur %s n'a pas assez d'argent.\n", j->nom);
        return false;
    }

    j->argent -= prix;
    p->nbhotels += nb;
    j->hotels += nb;
    printf("Le joueur %s a acheté %d hôtel(s). Il vous reste %d.\n", j->nom, nb, j->argent);

    return true;
}

int lancerDes() {
    return (rand() % 6 + 1) + (rand() % 6 + 1);
}

void deplacerJoueur(Joueur *joueur, int deplacement) {
    int oldPosition = joueur->position;
    joueur->position = (joueur->position + deplacement) % NUM_CASES;

    if (oldPosition > joueur->position || joueur->position == 0) {
        printf("%s a passé ou est tombé sur la case Départ. Recevez %d !\n", joueur->nom, START_BONUS);
        joueur->argent += START_BONUS;
        joueur->nbtour++;
    }

    printf("Le joueur %s est maintenant à la position %d.\n", joueur->nom, joueur->position);
}

void drawCommunityChestCard(Joueur *joueur) {

    int cardIndex = rand() % NUM_CARTE_CAISSE;
    printf("Carte Chance : %s\n", cartecaisse[cardIndex].description);
    switch (cardIndex) {
        case 0:
           joueur->position = 0;
            joueur->argent += 200;
            break;
        case 1:
           joueur->argent += 200;
            break;
        case 2:
            joueur->argent -= 50;
            break;
        case 3:
            joueur->argent += 50;
            break;
        case 4:
            break;
        case 5:
            joueur->position = JAIL_POSITION;
            joueur->enPrison = 1;
            break;
        case 6:
           joueur->argent += 100;
            break;
        case 7:
            joueur->argent += 100;
            break;
        case 8:
           joueur->argent -= 50;
            break;
        case 9:
            joueur->argent -= 150;
            break;
        case 10:
           joueur->argent += 25;
            break;
        case 11:
            joueur->argent += 100;
            break;
        case 12:
            joueur->argent += 100;
            break;
        case 13:
            joueur->argent += 50;
            break;
        case 14:
             joueur->argent -= (40 * joueur->maisons + 115 * joueur->hotels);
            break;
    }
    printf("Argent actuel : %d Dinars\n", joueur->argent);
}
void drawChanceCard(Joueur *joueur) {
    int cardIndex = rand() % NUM_CARTE_CHANCE;
    printf("Carte Chance : %s\n", cartechance[cardIndex].description);

    switch (cardIndex) {
        case 0:
            joueur->position = 0;
            joueur->argent += 200;
            break;
        case 1:
            joueur->argent += 150;
            break;
        case 2:
            joueur->argent -= 100;
            break;
        case 3:
            joueur->position += 3;
            break;
        case 4:
            joueur->position = JAIL_POSITION;
            joueur->enPrison = 1;
            break;
        case 5:
            joueur->argent += 50;
            break;
        case 6:
            joueur->argent -= 50;
            break;
        case 7:
            joueur->position -= 3;
            if (joueur->position < 0) joueur->position += NUM_CASES;
            break;
        case 8:
            joueur->argent += 100;
            break;
        case 9:
            joueur->argent -= 150;
            break;
        case 10:
            joueur->argent += 25;
            break;
        case 11:
            joueur->argent += 75;
            break;
        case 12:
            joueur->argent -= 200;
            break;
        case 13:
            joueur->argent += 200;
            break;
    }

    printf("Argent actuel : %d Dinars\n", joueur->argent);
}


void gererCase(Joueur *joueur, Board *board) {
    Case *currentCase = &board->cases[joueur->position];

    if (joueur->position == 30) {
        joueur->enPrison = 1;
    }

    if (joueur->position == JAIL_POSITION) {
        printf("%s est en visite à la prison.\n", joueur->nom);
    } else if (joueur->position == 2 || joueur->position == 33 || joueur->position==17) {
        printf("%s est tombé sur une case Caisse de communauté.\n", joueur->nom);
        drawCommunityChestCard(joueur);
    }else if (joueur->position==7 || joueur->position==36 || joueur->position==22){

	  printf("%s est tombé sur une case chance .\n", joueur->nom);
        drawChanceCard(joueur);
    } else if (strcmp(currentCase->type, "Propriete") == 0) {
        if (currentCase->owner == -1) {
            printf("%s est sur une propriété non achetée (%s).\n", joueur->nom, currentCase->name);
            printf("Voulez-vous acheter cette propriété pour %d Dinars ? (1 = Oui, 0 = Non): ", currentCase->price);
            int decision;
            if (scanf("%d", &decision) != 1) {
                printf("Entrée invalide. Vous ne pouvez pas acheter la propriété.\n");
                return;
            }

            if (decision == 1) {
                Propriete propriete = {
                    .cases = *currentCase,
                    .nbmaisons = 0,
                    .nbhotels = 0,
                    .prixmaison = 50.0,
                    .prixhotels = 100.0
                };
                if (acheterPropriete(&propriete, joueur)) {
                    currentCase->owner = joueur->id;

                    printf("Félicitations ! Le joueur %s a acheté %s.\n  id = %d \n", joueur->nom, currentCase->name,currentCase->owner);
                }
            }
        } else if (currentCase->owner == joueur->id) {
            printf("%s possède déjà cette propriété (%s).\n", joueur->nom, currentCase->name);
            printf("Voulez-vous acheter des maisons sur cette propriété ? (1 = Oui, 0 = Non): ");
            int decision;
            if (scanf("%d", &decision) != 1) {
                printf("Entrée invalide. Vous ne pouvez pas acheter des maisons.\n");
                return;
            }

            if (decision == 1) {
                int nbMaisons;
                printf("Combien de maisons voulez-vous acheter ? (max 4): ");
                scanf("%d", &nbMaisons);
                achetermaison((Propriete *)currentCase, joueur, nbMaisons);
            }
        } else {
            printf("Cette propriété appartient au joueur ID %d.\n", currentCase->owner);
            Propriete propriete = {
                .cases = *currentCase,
                .nbmaisons = 0,
                .nbhotels = 0,
                .prixmaison = 50.0,
                .prixhotels = 100.0
            };
            payerloyer(&propriete, joueur);
        }
    } else {
        printf("%s est sur une case normale.\n", joueur->nom);
    }
}

void tourJoueur(Joueur *joueur, Board *board) {
    if (joueur == NULL || board == NULL) {
        printf("Erreur : pointeur NULL détecté.\n");
        return;
    }

    if (joueur->position == 10 || joueur->position == 30) {
        printf("%s est en prison.\n", joueur->nom);
        printf("Voulez-vous payer %d Dinars pour sortir de prison ? (1 = Oui, 0 = Non): ", JAIL_FINE);
        int decision;
        if (scanf("%d", &decision) != 1) {
            printf("Entrée invalide.\n");
            return;
        }

        if (decision == 1 && joueur->argent >= JAIL_FINE) {
            joueur->argent -= JAIL_FINE;
            joueur->enPrison = 0;
            printf("%s a payé et est maintenant libre.\n", joueur->nom);
        } else {
            int de1 = rand() % 6 + 1;
            int de2 = rand() % 6 + 1;
            printf("Résultat des dés: %d et %d\n", de1, de2);

            if (de1 + de2 == 12) {
                joueur->enPrison = 0;
                printf("%s a lancé un double et sort de prison gratuitement !\n", joueur->nom);
                deplacerJoueur(joueur, de1 + de2);
            } else {
                if (joueur->argent >= JAIL_PENALTY) {
                    joueur->argent -= JAIL_PENALTY;
                    printf("%s reste en prison et perd %d Dinars.\n", joueur->nom, JAIL_PENALTY);
                } else {
                    printf("%s n'a pas assez d'argent pour payer la pénalité.\n", joueur->nom);
                }
                return;
            }
        }
    }

    printf("Appuyez sur Entrée pour lancer les dés...");
    fflush(stdin);  // Vide le buffer d'entrée
    getchar();

    int deplacement = lancerDes();
    printf("Lancer de dés: %d\n", deplacement);

    deplacerJoueur(joueur, deplacement);
    gererCase(joueur, board);
    printf("Position actuelle: %d, Argent: %d Dinars\n", joueur->position, joueur->argent);
}

void jouerSon(const char *fichier) {
    mciSendString("stop mp3", NULL, 0, 0);
    mciSendString("close mp3", NULL, 0, 0);

    char commande[256];
    snprintf(commande, sizeof(commande), "open \"%s\" type mpegvideo alias mp3", fichier);
    if (mciSendString(commande, NULL, 0, 0) != 0) {
        printf("Erreur lors de l'ouverture du fichier %s\n", fichier);
        return;
    }

    mciSendString("play mp3", NULL, 0, 0);
    Sleep(1000);
}



void verifierVictoire(Joueur joueurs[], int nb) {
    int i;
    for (i = 0; i < nb; i++) {
        if (joueurs[i].argent >= GAIN) {


            jouerSon("tada.mp3");
            printf("%s a gagné la partie avec %d$!\n", joueurs[i].nom, joueurs[i].argent);
            jouerSon("tara.mp3");
            Sleep(5000);

            exit(0);
        }
    }
}

int main() {
   
Joueur joueurs[MAX_JOUEURS];
    srand(time(NULL));

    Board board;
    loadBoardFromFile(&board,"board.txt");
    loadCarteCaisseFromFile("caisse.txt");
    loadCarteChanceFromFile("chance.txt");
   int nbJoueurs,i;

    initialiserJoueurs(joueurs, &nbJoueurs);
    for(i=0;i<nbJoueurs;i++){
    	joueurs[i].id=i;
}


jouerSon("gamestart.mp3");

    printf("\n### Début du jeu ###\n");

    int joueurActuel = 0;
    while (1) {
        printf("\nC'est le tour de %s.\n", joueurs[joueurActuel].nom);
        tourJoueur(&joueurs[joueurActuel], &board);

        joueurActuel = (joueurActuel + 1) % nbJoueurs;
        verifierVictoire(joueurs,nbJoueurs);
        displayJoueurs(joueurs, nbJoueurs);
}

      // Initialisation d'un joueur
    strcpy(joueurs[0].nom, "Testeur");
    joueurs[0].argent = 1500;
    joueurs[0].position = 0;
    joueurs[0].id = 0;
    joueurs[0].enPrison = 0;
    joueurs[0].nbtour = 1;

    // Tester les cartes Caisse (cases 2 et 33)
    printf("\n--- Test de la Caisse de Communauté (Case 2) ---\n");
    joueurs[0].position = 2;
    gererCase(&joueurs[0], &board);

    printf("\n--- Test de la Caisse de Communauté (Case 33) ---\n");
    joueurs[0].position = 33;
    gererCase(&joueurs[0], &board);

    // Tester les cartes Chance (cases 7 et 36)
    printf("\n--- Test de la Carte Chance (Case 7) ---\n");
    joueurs[0].position = 7;
    gererCase(&joueurs[0], &board);

    printf("\n--- Test de la Carte Chance (Case 36) ---\n");
    joueurs[0].position = 36;
    gererCase(&joueurs[0], &board);
    Propriete propriete1 = {{0, "Rue de la Paix", "propriete", 400, 50, -1}, 0, 0, 50.0, 100.0};


   printf("--------------------------------\n");
   printf("Loyer calculé : %d \n", calculerLoyer(&propriete1));
    acheterPropriete(&propriete1, &joueurs[0]);
    printf("--------------------------------\n");

    achetermaison(&propriete1, &joueurs[0], 2);
    printf("--------------------------------\n");

   acheterhotel(&propriete1, &joueurs[0], 1);
    printf("--------------------------------\n");

    payerloyer(&propriete1, &joueurs[1]);
    printf("--------------------------------\n");

    displayJoueurs(joueurs, nbJoueurs);
    return 0;
}
