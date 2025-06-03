#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    char name[50];
    int position;
    int balance;
} Player;

Player players[2];

void init_game() {
    strcpy(players[0].name, "Joueur 1");
    players[0].position = 0;
    players[0].balance = 1500;

    strcpy(players[1].name, "Joueur 2");
    players[1].position = 0;
    players[1].balance = 1500;
}

char* play_turn(int player_id, int dice_roll) {
    static char message[100];
    if (player_id < 0 || player_id > 1 || dice_roll < 1 || dice_roll > 6) {
        return "Erreur: ID du joueur ou résultat des dés invalide.";
    }
    
    players[player_id].position = (players[player_id].position + dice_roll) % 40;
    snprintf(message, sizeof(message), "%s a avancé à la position %d\n", players[player_id].name, players[player_id].position);
    return message;
}

void print_game_state(char* state) {
    snprintf(state, 500, "État du jeu:\n");
    int i;
    for ( i = 0; i < 2; i++) {
        snprintf(state + strlen(state), 500 - strlen(state), "%s - Position: %d, Solde: $%d\n", players[i].name, players[i].position, players[i].balance);
    }
}

int main(int argc, char *argv[]) {
    init_game();
    char game_state[500];

    if (argc > 1) {
        if (strcmp(argv[1], "play_turn") == 0 && argc == 4) {
            int player_id = atoi(argv[2]);
            int dice_roll = atoi(argv[3]);
            char* result = play_turn(player_id, dice_roll);
            printf("%s", result);
        } else if (strcmp(argv[1], "state") == 0) {
            print_game_state(game_state);
            printf("%s", game_state);
        } else {
            printf("Commande inconnue\n");
        }
    }

    return 0;
}

