import random
import os
import time
from collections import Counter
import colorama
import json

# Инициализация colorama
colorama.init(autoreset=True)

# --- 1. Константы и Настройки ---
C_RED, C_YELLOW, C_CYAN, C_GREEN, C_WHITE, C_RESET = colorama.Fore.RED, colorama.Fore.YELLOW, colorama.Fore.CYAN, colorama.Fore.GREEN, colorama.Fore.WHITE, colorama.Style.RESET_ALL
C_MAGENTA, C_BRIGHT = colorama.Fore.MAGENTA, colorama.Style.BRIGHT

# --- 2. Логика Игры ---
SUITS_MAP = {'H': '♥', 'D': '♦', 'C': '♣', 'S': '♠'}; RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']; RANK_VALUES = {rank: i for i, rank in enumerate(RANKS, 2)}
HAND_SCORES = {'Флеш-рояль': {'chips': 150, 'mult': 12}, 'Стрит-флеш': {'chips': 100, 'mult': 8},'Каре': {'chips': 80, 'mult': 7}, 'Фулл-хаус': {'chips': 60, 'mult': 4},'Флеш': {'chips': 50, 'mult': 4}, 'Стрит': {'chips': 40, 'mult': 3},'Сет': {'chips': 30, 'mult': 2}, 'Две пары': {'chips': 20, 'mult': 2},'Одна пара': {'chips': 10, 'mult': 1}, 'Старшая карта': {'chips': 5, 'mult': 1},}
def create_deck(): return [rank + suit for suit in SUITS_MAP.keys() for rank in RANKS]
def evaluate_hand(hand_cards_str, vouchers):
    if not hand_cards_str or len(hand_cards_str) > 5: return "Неверная рука", 0, 0
    ranks = [c[:-1] for c in hand_cards_str]; suits = [c[-1] for c in hand_cards_str]; rank_counts = Counter(ranks); counts = sorted(rank_counts.values(), reverse=True)
    is_flush = len(set(suits)) == 1 and len(hand_cards_str) >= 3
    numeric_ranks = sorted([RANK_VALUES[r] for r in ranks])
    is_straight = len(set(numeric_ranks)) == len(hand_cards_str) and (numeric_ranks[-1] - numeric_ranks[0] == len(hand_cards_str) - 1) and len(hand_cards_str) >= 3
    if set(ranks) == {'A', '2', '3', '4', '5'}: is_straight = True
    if is_straight and is_flush and set(ranks) == {'10', 'J', 'Q', 'K', 'A'}: hand_name = 'Флеш-рояль'
    elif is_straight and is_flush: hand_name = 'Стрит-флеш'
    elif counts == [2, 1] and len(hand_cards_str) == 3: hand_name = 'Одна пара'
    elif counts[0] == 4: hand_name = 'Каре'
    elif counts == [3, 2]: hand_name = 'Фулл-хаус'
    elif is_flush: hand_name = 'Флеш'
    elif is_straight: hand_name = 'Стрит'
    elif counts[0] == 3: hand_name = 'Сет'
    elif counts == [2, 2, 1]: hand_name = 'Две пары'
    elif counts[0] == 2: hand_name = 'Одна пара'
    else: hand_name = 'Старшая карта'
    chips, mult = HAND_SCORES[hand_name]['chips'], HAND_SCORES[hand_name]['mult']
    if 'holo_spades' in vouchers and any(s == 'S' for s in suits): mult += 2
    return hand_name, chips, mult

# --- 3. Классы ---
class Card:
    def __init__(self, card_str): self.card_str, self.bonus_chips, self.bonus_mult = card_str, 0, 0
class Joker:
    def __init__(self, name, description, cost): self.name, self.description, self.cost = name, description, cost
    def apply(self, chips, mult, hand, hand_name): return chips, mult
    def on_round_end(self, game): pass
class Joker_PlusMult(Joker):
    def apply(self, chips, mult, hand, hand_name): return chips, mult + 4
class Joker_PairBonus(Joker):
    def apply(self, chips, mult, hand, hand_name):
        if hand_name == 'Одна пара': return chips, mult + 8
        return chips, mult
class Joker_Greed(Joker):
    def on_round_end(self, game): game.money += game.hands_left
class TarotCard:
    def __init__(self, name, description, cost): self.name, self.description, self.cost = name, description, cost
    def requires_target(self): return True
    def apply(self, game, target_card_idx=None): pass
class Tarot_Sun(TarotCard):
    def apply(self, game, target_card_idx=None): game.player_hand[target_card_idx].bonus_mult += 4
class Tarot_Hermit(TarotCard):
    def requires_target(self): return False
    def apply(self, game, target_card_idx=None): game.money += 20
class Voucher:
    def __init__(self, name, description, cost, code): self.name, self.description, self.cost, self.code = name, description, cost, code
class Amulet:
    def __init__(self, name, description): self.name, self.description = name, description
    def apply_start(self, game): pass
    def apply_shop_restock(self, game, shop_list): return shop_list
    def apply_end_round(self, game): pass
class Amulet_ExtraShopSlot(Amulet):
    def apply_shop_restock(self, game, shop_list):
        new_items = random.sample(JOKER_POOL + TAROT_POOL, k=2)
        shop_list = new_items + shop_list
        random.shuffle(shop_list)
        return shop_list
class Amulet_GoldenTicket(Amulet):
    def apply_start(self, game): game.money += 20
class Amulet_BrokenClock(Amulet):
    def apply_start(self, game): game.base_stats['hands'] += 1
class Amulet_Magnet(Amulet):
    def apply_start(self, game): game.base_stats['free_discard'] = True
JOKER_POOL = [Joker_PlusMult("Джокер", "+4 к множителю", 4), Joker_PairBonus("Мастер Пар", "+8 множ. за 'Пару'", 5), Joker_Greed("Жадность", "+$1 за каждую несыгранную руку", 7)]
TAROT_POOL = [Tarot_Sun("Солнце", "+4 множ. на карту", 3), Tarot_Hermit("Отшельник", "Дает $20", 2)]
VOUCHER_POOL = [Voucher("Ваучер на скидку", "Все в магазине -25%", 20, "discount"), Voucher("Голо-ваучер", "Пики дают +2 множ.", 15, "holo_spades"), Voucher("Реролл-ваучер", "1-й реролл бесплатен", 10, "free_reroll")]
AMULET_POOL = [Amulet("Стеклянный Глаз", "В магазине всегда 8 товаров"), Amulet_ExtraShopSlot("Расширенный Магазин", "В магазине на 2 товара больше"), Amulet_GoldenTicket("Золотой Билет", "Начать с +$20"), Amulet_BrokenClock("Сломанные Часы", "+1 рука на весь забег"), Amulet_Magnet("Магнит", "Первый сброс в раунде бесплатный")]
class Boss:
    def __init__(self, name, desc): self.name, self.debuff_desc = name, desc
    def apply_debuff(self, hand): return hand
    def modify_game_state(self, game): pass
class Boss_TheWall(Boss):
    def modify_game_state(self, game): game.hands_left -= 1
BOSS_POOL = [Boss_TheWall("Стена", "Вы начинаете с -1 рукой")]

# ... (все функции отрисовки и HUD без изменений)
def clear_screen(): os.system('cls' if os.name == 'nt' else 'clear')
def print_cards(hand, selected_indices, settings):
    if settings['graphics'] == 'Minimal':
        lines = [[]]
        for i, card_obj in enumerate(hand):
            card_str, b_chips, b_mult = card_obj.card_str, card_obj.bonus_chips, card_obj.bonus_mult
            is_selected = i in selected_indices
            color = C_YELLOW if is_selected else C_WHITE
            bonus_str = ("" if b_chips == 0 else f"+{b_chips}C") + ("" if b_mult == 0 else f"+{b_mult}M")
            lines[0].append(f"{color}[{card_str.ljust(3)} {bonus_str}]{C_RESET}")
        print(" ".join(lines[0])); return
    lines = [''] * 7
    for i, card_obj in enumerate(hand):
        card_str, b_chips, b_mult = card_obj.card_str, card_obj.bonus_chips, card_obj.bonus_mult
        rank, suit_key = card_str[:-1], card_str[-1]; suit_char = SUITS_MAP[suit_key]; is_selected = i in selected_indices
        suit_color = C_RED if suit_key in 'HD' else C_WHITE; border_color = C_YELLOW if is_selected else C_WHITE
        rank_l = rank.ljust(2); rank_r = rank.rjust(2); bonus_str = ("" if b_chips == 0 else f"+{b_chips}C ") + ("" if b_mult == 0 else f"+{b_mult}M")
        lines[0] += f" {border_color}┌───────┐{C_RESET} "; lines[1] += f" {border_color}│{suit_color}{rank_l}{C_RESET}     {border_color}│{C_RESET} "; lines[2] += f" {border_color}│{C_CYAN}{bonus_str.strip().ljust(7)}{border_color}│{C_RESET} "; lines[3] += f" {border_color}│   {suit_color}{suit_char}{C_RESET}   {border_color}│{C_RESET} "; lines[4] += f" {border_color}│       {border_color}│{C_RESET} "; lines[5] += f" {border_color}│     {suit_color}{rank_r}{C_RESET}{border_color}│{C_RESET} "; bottom_content = f"-[{i+1}]-".center(7, '─'); lines[6] += f" {border_color}└{C_WHITE}{bottom_content}{border_color}┘{C_RESET} "
    for line in lines: print(line)
def print_hud(game):
    width = 88; tarot_count = len(game.tarot_cards)
    print(f"{C_WHITE}{C_BRIGHT}{'='*width}")
    ante_str = f"АНТЕ {game.ante}"; target_str = f"Цель: {game.target_score}"; ante_colored = f"{C_CYAN}{ante_str}"; target_colored = f"{C_WHITE}Цель: {C_YELLOW}{game.target_score}"
    visible_len_l1 = len(f"АНТЕ {game.ante}")
    print(f"{ante_colored}{target_colored.rjust(width - visible_len_l1)}")
    print(f"{C_WHITE}СЧЕТ: {C_GREEN}{game.current_score}")
    print(f"{C_WHITE}{C_BRIGHT}{'='*width}")
    parts = [f"{C_WHITE}Рук: {C_CYAN}{game.hands_left}", f"{C_WHITE}Сбросов: {C_CYAN}{game.discards_left}", f"{C_WHITE}Таро: {C_CYAN}{tarot_count}", f"{C_WHITE}Деньги: {C_GREEN}${game.money}"]
    print("    ".join(parts))
    print(f"{C_WHITE}{C_BRIGHT}{'='*width}\n")
def print_jokers(jokers):
    if not jokers: return
    print(f"{C_WHITE}ВАШИ ДЖОКЕРЫ:"); joker_lines = [[] for _ in range(3)];
    for joker in jokers:
        name = joker.name.center(18); joker_lines[0].append(f"{C_MAGENTA}┌──────────────────┐"); joker_lines[1].append(f"{C_MAGENTA}│{C_WHITE}{name}{C_MAGENTA}│"); joker_lines[2].append(f"{C_MAGENTA}└──────────────────┘")
    if len(joker_lines[0]) > 0:
        for line_parts in joker_lines: print(" ".join(line_parts))
    print("")
def animate_score(game, start_score, end_score):
    step = max(1, (end_score - start_score) // 20)
    for i in range(start_score, end_score + 1, step):
        clear_screen(); game.current_score = i; print_hud(game); print_jokers(game.jokers); print("ВАША РУКА:"); print_cards(game.player_hand, [], game.settings); time.sleep(0.01)
    game.current_score = end_score

# --- 5. Основной Класс Игры ---
class Game:
    def __init__(self, settings, challenge=None, amulet=None):
        self.settings, self.challenge, self.amulet = settings, challenge, amulet; self.ante, self.money, self.jokers, self.tarot_cards, self.vouchers = 1, 10, [], [], []; self.upgrades = {'hands': 0, 'discards': 0, 'jokers': 0}; self.base_stats = {'hands': 4, 'discards': 3, 'joker_slots': 5, 'free_discard': False}; self.game_state = "ROUND_START"; self.deck, self.player_hand, self.selected_indices = [], [], []; self.target_score, self.current_score, self.hands_left, self.discards_left = 0, 0, 0, 0; self.current_boss, self.discards_used_this_round = None, False; self.shop_reroll_cost = 3; self.next_round_is_boss = False; self.next_round_discards = None
        if self.amulet: self.amulet.apply_start(self)
        if self.challenge == 'shrinking_deck': self.full_deck = create_deck(); random.shuffle(self.full_deck)
    def get_max_joker_slots(self): return self.base_stats['joker_slots'] + self.upgrades['jokers']
    def run(self):
        while self.game_state not in ["GAME_OVER", "RUN_COMPLETE"]:
            if self.game_state == "EVENT": self.run_event()
            if self.game_state == "ROUND_START": self.start_new_round()
            if self.game_state == "PLAYING": self.play_round()
            if self.game_state == "SHOP": self.run_shop()
        self.run_game_over()
    def start_new_round(self):
        self.target_score = self.ante * 100 * (1 + (self.ante // 3)); self.current_score = 0; self.hands_left = self.base_stats['hands'] + self.upgrades['hands']; self.discards_left = self.next_round_discards if self.next_round_discards is not None else self.base_stats['discards'] + self.upgrades['discards']; self.next_round_discards = None; self.discards_used_this_round = False
        if self.challenge != 'shrinking_deck':
            deck_str = create_deck(); random.shuffle(deck_str); self.deck = [Card(s) for s in deck_str]
        else: self.deck = self.full_deck
        self.player_hand = [self.deck.pop() for _ in range(8) if self.deck]
        self.selected_indices = []; self.current_boss = None
        if self.ante % 3 == 0 or self.next_round_is_boss:
            self.current_boss = random.choice(BOSS_POOL); self.current_boss.modify_game_state(self); self.next_round_is_boss = False
        self.game_state = "PLAYING"
    def play_round(self):
        round_active = True; free_discard_used = False
        while round_active:
            clear_screen(); print_hud(self); print_jokers(self.jokers)
            if self.current_boss: print(f"{C_RED}{C_BRIGHT}ЭФФЕКТ БОССА: {self.current_boss.name} - {self.current_boss.debuff_desc}\n")
            print("ВАША РУКА:"); print_cards(self.player_hand, self.selected_indices, self.settings)
            selected_objs = [self.player_hand[i] for i in self.selected_indices]; selected_strs = [c.card_str for c in selected_objs]
            hand_to_eval = self.current_boss.apply_debuff(selected_strs) if self.current_boss else selected_strs
            hand_name, base_chips, base_mult = evaluate_hand(hand_to_eval, self.vouchers)
            bonus_chips = sum(c.bonus_chips for c in selected_objs); bonus_mult = sum(c.bonus_mult for c in selected_objs); final_chips, final_mult = base_chips + bonus_chips, base_mult + bonus_mult
            for joker in self.jokers: final_chips, final_mult = joker.apply(final_chips, final_mult, selected_strs, hand_name)
            if selected_objs: print(f"\n{C_YELLOW}{C_BRIGHT}Выбрано: {hand_name} (Итог: {final_chips} фишек x {final_mult} множитель)")
            
            action = input(f"\n{C_WHITE}> Введите номера (1-8), '{C_GREEN}p{C_WHITE}', '{C_CYAN}d{C_WHITE}', '{C_MAGENTA}t{C_WHITE}': ").lower()
            if action == 't': self.use_tarot(); continue
            elif action == 'p':
                if not selected_objs or self.hands_left == 0: continue
                old_score = self.current_score; score_from_hand = final_chips * final_mult; self.hands_left -= 1
                animate_score(self, old_score, old_score + score_from_hand); print(f"{C_YELLOW}{C_BRIGHT} +{score_from_hand} очков!{C_RESET}"); time.sleep(1)
                if self.challenge == 'shrinking_deck': self.player_hand = [c for i, c in enumerate(self.player_hand) if i not in self.selected_indices]
                else:
                    new_hand = [c for i, c in enumerate(self.player_hand) if i not in self.selected_indices]
                    for _ in range(8-len(new_hand)):
                        if not self.deck: self.deck = [Card(s) for s in create_deck()]; random.shuffle(self.deck)
                        if self.deck: new_hand.append(self.deck.pop())
                    self.player_hand = new_hand
                self.selected_indices = []
            elif action == 'd':
                is_free = self.base_stats.get('free_discard', False) and not free_discard_used
                if not selected_objs or (self.discards_left == 0 and not is_free): continue
                if not is_free: self.discards_left -= 1
                else: free_discard_used = True
                self.discards_used_this_round = True
                if self.challenge == 'shrinking_deck': self.player_hand = [c for i, c in enumerate(self.player_hand) if i not in self.selected_indices]
                else:
                    new_hand = [c for i, c in enumerate(self.player_hand) if i not in self.selected_indices]
                    for _ in range(8 - len(new_hand)):
                        if not self.deck: self.deck = [Card(s) for s in create_deck()]; random.shuffle(self.deck)
                        if self.deck: new_hand.append(self.deck.pop())
                    self.player_hand = new_hand
                self.selected_indices = []
            else:
                try:
                    cleaned_action = action.replace(" ", ""); new_indices = [int(c.strip()) - 1 for c in cleaned_action.split(',')]
                    for i in new_indices:
                        if 0 <= i < len(self.player_hand):
                            if i in self.selected_indices: self.selected_indices.remove(i)
                            else: self.selected_indices.append(i)
                except (ValueError, IndexError): pass
            if self.current_score >= self.target_score:
                money_won = 10 + self.hands_left + self.discards_left; self.money += money_won
                for joker in self.jokers: joker.on_round_end(self)
                if self.amulet: self.amulet.apply_end_round(self)
                print(f"\n{C_GREEN}{C_BRIGHT}🎉 ПОБЕДА! Заработано ${money_won}.{C_RESET}"); print("Нажмите Enter..."); input()
                self.ante += 1
                if self.current_boss is None and random.random() < 0.25: self.game_state = "EVENT"
                else: self.game_state = "SHOP"
                round_active = False
            is_round_over = self.hands_left == 0 and action == 'p'
            if self.challenge == 'shrinking_deck' and not self.player_hand and (len(self.deck) < (8 - len(self.player_hand))): is_round_over = True
            if is_round_over:
                if self.ante > 8 and self.challenge: self.game_state = "RUN_COMPLETE"
                else: self.game_state = "GAME_OVER"
                round_active = False
    def use_tarot(self):
        if not self.tarot_cards: print(f"{C_RED}У вас нет карт Таро!{C_RESET}"); time.sleep(1.5); return
        print(f"\n{C_WHITE}Какую карту Таро использовать?");
        for i, tarot in enumerate(self.tarot_cards): print(f"  [{i+1}] {tarot.name} - {tarot.description}")
        choice_str = input("> Введите номер или 'c' для отмены: ").lower()
        if choice_str == 'c': return
        try:
            tarot_idx = int(choice_str) - 1
            if 0 <= tarot_idx < len(self.tarot_cards):
                tarot_to_use = self.tarot_cards[tarot_idx]; target_card_idx = None
                if tarot_to_use.requires_target():
                    target_str = input("> Выберите карту в руке (1-8) для применения эффекта: ")
                    target_card_idx = int(target_str) - 1
                    if not (0 <= target_card_idx < len(self.player_hand)): raise IndexError
                tarot_to_use.apply(self, target_card_idx); self.tarot_cards.pop(tarot_idx); time.sleep(2)
        except (ValueError, IndexError): print(f"{C_RED}Неверный выбор!{C_RESET}"); time.sleep(1.5)
    def run_shop(self):
        shop_list = []; free_reroll = 'free_reroll' in self.vouchers
        def restock_shop():
            nonlocal shop_list
            shop_list = random.sample(JOKER_POOL, k=1) + random.sample(TAROT_POOL, k=1)
            if random.random() < 0.2 and len(self.vouchers) < len(VOUCHER_POOL):
                available_vouchers = [v for v in VOUCHER_POOL if v.code not in self.vouchers]
                if available_vouchers: shop_list.append(random.choice(available_vouchers))
            upgrades = [{"name": "+1 Рука", "cost": 10 + 5 * self.upgrades['hands'], "action": "upgrade_hands"}, {"name": "+1 Сброс", "cost": 8 + 4 * self.upgrades['discards'], "action": "upgrade_discards"}, {"name": "+1 Слот Джокера", "cost": 20 + 10 * self.upgrades['jokers'], "action": "upgrade_jokers", "maxed": self.get_max_joker_slots() >= 6}, {"name": "Бустер Таро (2шт)", "cost": 6, "action": "buy_tarot_pack"}, {"name": "Реролл Магазина", "cost": self.shop_reroll_cost if not free_reroll else 0, "action": "reroll"},]
            shop_list += upgrades
            if self.amulet: shop_list = self.amulet.apply_shop_restock(self, shop_list)
        restock_shop()
        while True:
            clear_screen(); print(f"{C_YELLOW}{C_BRIGHT}{'='*30} МАГАЗИН {'='*30}"); print(f"{C_WHITE}Ваши деньги: {C_GREEN}${self.money}\n"); print_jokers(self.jokers); print(f"{C_WHITE}Товары в наличии:\n")
            for i, item in enumerate(shop_list):
                prefix = f"[{i+1}]"
                discount = 0.75 if 'discount' in self.vouchers else 1.0
                cost = int(item.cost * discount) if isinstance(item, (Joker, TarotCard, Voucher)) else int(item['cost'] * discount)
                
                if isinstance(item, (Joker, TarotCard, Voucher)):
                    can_afford = self.money >= cost; price_color = C_GREEN if can_afford else C_RED; print(f"  {C_WHITE}{prefix} {item.name} - {item.description} ({price_color}${cost}{C_WHITE})")
                else:
                    is_maxed = item.get("maxed", False); can_afford = self.money >= cost; price_color = C_GREEN if can_afford and not is_maxed else C_RED; status = "(МАКС)" if is_maxed else f"(${cost})"; print(f"  {C_WHITE}{prefix} {item['name']} ({price_color}{status}{C_WHITE})")
            
            action = input(f"\n{C_WHITE}> Введите номер для покупки, '{C_RED}s{C_WHITE}' - продать, или '{C_CYAN}e{C_WHITE}', чтобы выйти: ").lower()
            if action == 'e': self.game_state = "ROUND_START"; break
            elif action == 's':
                if not self.jokers: print(f"{C_RED}У вас нет джокеров для продажи!{C_RESET}"); time.sleep(1.5); continue
                print(f"\n{C_WHITE}Какой джокер продать?");
                for i, joker in enumerate(self.jokers): print(f"  [{i+1}] {joker.name} (цена продажи: {C_GREEN}${joker.cost//2}{C_WHITE})")
                sell_action = input("> Введите номер или 'c' для отмены: ").lower()
                if sell_action == 'c': continue
                try:
                    joker_to_sell = self.jokers.pop(int(sell_action) - 1); sell_price = joker_to_sell.cost // 2; self.money += sell_price
                except (ValueError, IndexError): print(f"{C_RED}Неверный номер!{C_RESET}"); time.sleep(1.5)
            else:
                try:
                    choice_idx = int(action) - 1
                    if not (0 <= choice_idx < len(shop_list)): raise IndexError
                    item = shop_list[choice_idx]
                    discount = 0.75 if 'discount' in self.vouchers else 1.0
                    cost = int(item.cost * discount) if isinstance(item, (Joker, TarotCard, Voucher)) else int(item['cost'] * discount)
                    if self.money >= cost:
                        if isinstance(item, Joker) and len(self.jokers) < self.get_max_joker_slots(): self.money -= cost; self.jokers.append(item); shop_list.pop(choice_idx)
                        elif isinstance(item, Joker): print(f"{C_RED}Слоты для джокеров закончились!{C_RESET}"); time.sleep(1.5)
                        elif isinstance(item, TarotCard) and len(self.tarot_cards) < 2: self.money -= cost; self.tarot_cards.append(item); shop_list.pop(choice_idx)
                        elif isinstance(item, TarotCard): print(f"{C_RED}У вас уже 2 карты Таро!{C_RESET}"); time.sleep(1.5)
                        elif isinstance(item, Voucher): self.money -= cost; self.vouchers.append(item.code); shop_list.pop(choice_idx)
                        elif isinstance(item, dict):
                            if item.get("maxed", False): continue
                            if item['action'] == "reroll" and free_reroll: free_reroll = False
                            else: self.money -= cost
                            if item['action'] == "reroll": restock_shop(); continue
                            elif item['action'] == "upgrade_hands": self.upgrades['hands'] += 1
                            elif item['action'] == "upgrade_discards": self.upgrades['discards'] += 1
                            elif item['action'] == "upgrade_jokers": self.upgrades['jokers'] += 1
                            elif item['action'] == "buy_tarot_pack": self.tarot_cards.extend(random.sample(TAROT_POOL, k=min(2, 2 - len(self.tarot_cards))))
                            restock_shop()
                    else: print(f"{C_RED}Недостаточно денег!{C_RESET}"); time.sleep(1.5)
                except (ValueError, IndexError): pass
    def run_event(self):
        clear_screen(); print(f"\n{C_MAGENTA}{C_BRIGHT}{'~'*15} ЧАША СУДЬБЫ {'~'*15}\n")
        print("Перед вами таинственная чаша. От нее исходит странное свечение.")
        action = input(f"> {C_GREEN}[1] Испить{C_RESET} или {C_RED}[2] Проигнорировать{C_RESET}? ")
        if action == '1':
            outcomes = ['good_money', 'bad_money', 'free_joker', 'next_boss', 'no_discards', 'destroy_joker']
            outcome = random.choice(outcomes)
            print("\nВы делаете глоток..."); time.sleep(2)
            if outcome == 'good_money': self.money += 50; print(f"{C_GREEN}Вы чувствуете себя богаче! +$50!{C_RESET}")
            elif outcome == 'bad_money': self.money = max(0, self.money - 20); print(f"{C_RED}Ваши карманы кажутся легче... -$20!{C_RESET}")
            elif outcome == 'free_joker' and len(self.jokers) < self.get_max_joker_slots(): self.jokers.append(random.choice(JOKER_POOL)); print(f"{C_GREEN}Из чаши выпадает Джокер!{C_RESET}")
            elif outcome == 'next_boss': self.next_round_is_boss = True; print(f"{C_RED}Жидкость в чаше темнеет... Вы чувствуете приближение босса.{C_RESET}")
            elif outcome == 'no_discards': self.next_round_discards = 0; print(f"{C_RED}Ваши мысли путаются. В следующем раунде у вас не будет сбросов!{C_RESET}")
            elif outcome == 'destroy_joker' and self.jokers: destroyed = self.jokers.pop(random.randrange(len(self.jokers))); print(f"{C_RED}Вспышка света! Ваш джокер '{destroyed.name}' уничтожен!{C_RESET}")
            else: print(f"{C_WHITE}Ничего не происходит... пока что.{C_RESET}")
        else: print("\nВы мудро решаете не связываться с неизвестным.")
        print("\nНажмите Enter, чтобы войти в магазин..."); input(); self.game_state = "SHOP"
    def run_game_over(self):
        clear_screen(); 
        if self.game_state == "RUN_COMPLETE": print(f"\n{C_GREEN}{C_BRIGHT}🏆 ПОБЕДА! Вы прошли челлендж!{C_RESET}")
        else: print(f"\n{C_RED}{C_BRIGHT}💔 ПОРАЖЕНИЕ. Руки закончились.{C_RESET}")
        print(f"Вы дошли до {C_CYAN}Анте {self.ante}{C_RESET}")
        if self.settings['refund_on_loss'] and self.game_state == "GAME_OVER": self.money = 999; print(f"{C_YELLOW}Отец сделал додеп. Вы получили $999!{C_RESET}")
        print("Нажмите Enter, чтобы вернуться в меню..."); input()

# --- 6. Главное Меню и Запуск ---
def main_menu():
    settings = {'graphics': 'Full', 'refund_on_loss': False}; challenges = {'shrinking_deck': False}; save_slots = [None, None, None]
    
    def load_saves():
        for i in range(3):
            try:
                with open(f"savegame_{i}.json", 'r') as f: save_slots[i] = json.load(f).get('ante', 'Пусто')
            except FileNotFoundError: save_slots[i] = 'Пусто'

    def run_menu(title, options, current_values):
        while True:
            clear_screen(); print(f"{C_YELLOW}--- {title} ---")
            for i, option in enumerate(options):
                prefix = f"[{i+1}]"
                current_value = current_values.get(option, "")
                print(f"  {C_WHITE}{prefix} {option}: {C_YELLOW}{current_value}")
            print(f"\n{C_GREEN}Введите номер для выбора/изменения, 'e' - назад/выход")
            action = input("> ").lower()
            if action == 'e': return None
            try:
                choice = int(action) - 1
                if 0 <= choice < len(options): return options[choice]
            except ValueError: pass

    while True:
        load_saves()
        clear_screen(); print(f"{C_YELLOW}{C_BRIGHT}--- ПОКАТРО: Вечность ---{C_RESET}")
        
        save_options = [f"Слот 1 (Анте: {save_slots[0]})", f"Слот 2 (Анте: {save_slots[1]})", f"Слот 3 (Анте: {save_slots[2]})", "Челленджи", "Настройки", "Выход"]
        choice = run_menu("ГЛАВНОЕ МЕНЮ", save_options, {})
        
        if choice and "Слот" in choice:
            slot_idx = int(choice.split(' ')[1]) - 1
            if save_slots[slot_idx] != 'Пусто':
                print("Продолжение пока не реализовано") # Здесь будет логика загрузки
                time.sleep(2)
            else:
                amulets = random.sample(AMULET_POOL, k=min(3, len(AMULET_POOL)))
                print("\nВыберите Амулет для этого забега:")
                amulet_choice_str = run_menu("ВЫБОР АМУЛЕТА", [f"{a.name} - {a.description}" for a in amulets], {})
                if amulet_choice_str:
                    chosen_amulet = next((a for a in amulets if a.name in amulet_choice_str), None)
                    challenge = 'shrinking_deck' if challenges['shrinking_deck'] else None
                    game = Game(settings, challenge, chosen_amulet); game.run()

        elif choice == "Челленджи":
            challenge_options = {"Убывающая колода": "АКТИВЕН" if challenges['shrinking_deck'] else "НЕАКТИВЕН"}
            challenge_choice = run_menu("ЧЕЛЛЕНДЖИ", list(challenge_options.keys()), challenge_options)
            if challenge_choice == "Убывающая колода": challenges['shrinking_deck'] = not challenges['shrinking_deck']
        elif choice == "Настройки":
            settings_options = {"Графика": settings['graphics'], "Вернуть деньги после проеба": "ВКЛ" if settings['refund_on_loss'] else "ВЫКЛ"}
            setting_choice = run_menu("НАСТРОЙКИ", list(settings_options.keys()), settings_options)
            if setting_choice == "Графика": settings['graphics'] = 'Minimal' if settings['graphics'] == 'Full' else 'Full'
            elif setting_choice == "Вернуть деньги после проеба": settings['refund_on_loss'] = not settings['refund_on_loss']
        elif choice == "Выход" or choice is None: break

if __name__ == "__main__":
    try: main_menu()
    except Exception as e: print(f"\n{C_RED}Произошла непредвиденная ошибка: {e}{C_RESET}"); input("Нажмите Enter для выхода.")