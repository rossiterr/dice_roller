#!/usr/bin/env python3
"""
RPG Dice Roller - Linha de comando para rolagem de dados de RPG.
Suporta notação padrão: NdS, NdS+kN, NdS+dN, modificadores +/-.
"""

import argparse
import random
import re
import sys
from typing import List, Tuple, Optional


class DiceRoller:
    """Classe principal para interpretar e rolar dados em notação RPG."""

    # Regex para parsear expressões de dados
    # Grupos: quantidade, lados, keep/drop (k/d + número), modificador (+/- número)
    DICE_PATTERN = re.compile(
        r'^(\d+)d(\d+)(?:([kd])(\d+))?(?:([+-])(\d+))?$',
        re.IGNORECASE
    )

    def __init__(self):
        self.last_rolls: List[int] = []
        self.last_expression: str = ""

    def parse_expression(self, expression: str) -> Tuple[int, int, Optional[str], Optional[int], int]:
        """
        Parseia uma expressão de dados.
        Retorna: (quantidade, lados, keep_drop_type, keep_drop_num, modifier)
        """
        expression = expression.replace(" ", "")
        match = self.DICE_PATTERN.match(expression)

        if not match:
            raise ValueError(
                f"Formato inválido: '{expression}'. "
                "Use formatos como: 1d20+5, 3d6, 2d10-2, 2d20k1+3, 4d6d1"
            )

        qty = int(match.group(1))
        sides = int(match.group(2))
        kd_type = match.group(3).lower() if match.group(3) else None
        kd_num = int(match.group(4)) if match.group(4) else None
        mod_sign = match.group(5)
        mod_val = int(match.group(6)) if match.group(6) else 0

        if qty <= 0:
            raise ValueError("Quantidade de dados deve ser maior que zero.")
        if sides <= 0:
            raise ValueError("Número de lados deve ser maior que zero.")

        if kd_type:
            if kd_type == 'k' and (kd_num <= 0 or kd_num > qty):
                raise ValueError(f"Valor de keep (k{kd_num}) inválido para {qty} dados.")
            if kd_type == 'd' and (kd_num <= 0 or kd_num >= qty):
                raise ValueError(f"Valor de drop (d{kd_num}) inválido para {qty} dados.")

        modifier = mod_val if mod_sign == '+' else -mod_val if mod_sign == '-' else 0

        return qty, sides, kd_type, kd_num, modifier

    def roll_dice(self, qty: int, sides: int) -> List[int]:
        """Rola 'qty' dados de 'sides' lados."""
        return [random.randint(1, sides) for _ in range(qty)]

    def apply_keep_drop(self, rolls: List[int], kd_type: Optional[str], kd_num: Optional[int]) -> Tuple[List[int], List[int]]:
        """
        Aplica keep (manter maiores) ou drop (descartar menores).
        Retorna: (rolls_manidos, rolls_descartados)
        """
        if not kd_type or not kd_num:
            return rolls, []

        sorted_rolls = sorted(rolls, reverse=True)

        if kd_type == 'k':
            kept = sorted_rolls[:kd_num]
            dropped = sorted_rolls[kd_num:]
        else:  # 'd'
            kept = sorted_rolls[:-kd_num]
            dropped = sorted_rolls[-kd_num:]

        return kept, dropped

    def check_criticals(self, rolls: List[int], sides: int) -> List[str]:
        """Verifica críticos (max) e falhas críticas (min) em cada rolagem."""
        markers = []
        for roll in rolls:
            if roll == sides:
                markers.append("[CRITICO!]")
            elif roll == 1:
                markers.append("[FALHA CRITICA!]")
            else:
                markers.append("")
        return markers

    def roll(self, expression: str) -> dict:
        """Executa a rolagem completa e retorna dicionário com resultados."""
        self.last_expression = expression
        qty, sides, kd_type, kd_num, modifier = self.parse_expression(expression)

        # Rola os dados
        raw_rolls = self.roll_dice(qty, sides)
        self.last_rolls = raw_rolls[:]

        # Aplica keep/drop
        kept_rolls, dropped_rolls = self.apply_keep_drop(raw_rolls, kd_type, kd_num)

        # Verifica críticos
        crit_markers = self.check_criticals(raw_rolls, sides)

        # Calcula totais
        kept_sum = sum(kept_rolls)
        total = kept_sum + modifier

        return {
            "expression": expression,
            "qty": qty,
            "sides": sides,
            "kd_type": kd_type,
            "kd_num": kd_num,
            "modifier": modifier,
            "raw_rolls": raw_rolls,
            "kept_rolls": kept_rolls,
            "dropped_rolls": dropped_rolls,
            "crit_markers": crit_markers,
            "kept_sum": kept_sum,
            "total": total
        }

    def format_output(self, result: dict) -> str:
        """Formata a saída detalhada da rolagem."""
        lines = []
        expr = result["expression"]

        lines.append(f"[DICE] Rolagem: {expr}")
        lines.append("-" * 40)

        # Mostra cada dado individual
        raw = result["raw_rolls"]
        markers = result["crit_markers"]

        if result["kd_type"]:
            kept = result["kept_rolls"]
            dropped = result["dropped_rolls"]
            kd_symbol = "k" if result["kd_type"] == "k" else "d"
            kd_num = result["kd_num"]

            lines.append(f"Dados rolados: {raw}")
            lines.append(f"  -> Mantidos ({kd_symbol}{kd_num}): {kept} = {result['kept_sum']}")
            if dropped:
                lines.append(f"  -> Descartados: {dropped}")
        else:
            roll_strs = []
            for i, (roll, marker) in enumerate(zip(raw, markers)):
                s = str(roll)
                if marker:
                    s += f" {marker}"
                roll_strs.append(s)
            lines.append(f"Dados rolados: [{', '.join(roll_strs)}]")
            lines.append(f"  -> Soma: {result['kept_sum']}")

        # Modificador
        mod = result["modifier"]
        if mod != 0:
            sign = "+" if mod > 0 else ""
            lines.append(f"Modificador: {sign}{mod}")

        # Total
        lines.append("-" * 40)
        lines.append(f"[OK] TOTAL: {result['total']}")

        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="RPG Dice Roller - Rolador de dados para RPG via linha de comando",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python dice_roller.py "1d20+5"
  python dice_roller.py "3d6"
  python dice_roller.py "2d10-2"
  python dice_roller.py "2d20k1+3"   # Vantagem: mantém o maior
  python dice_roller.py "4d6d1"      # Descarta o menor (comum para atributos)
  python dice_roller.py "1d100"      # Percentual
  python dice_roller.py "2d6+3" --repetir 5
        """
    )

    parser.add_argument(
        "expression",
        nargs="?",
        help="Expressão de dados (ex: 1d20+5, 3d6, 2d20k1+3)"
    )

    parser.add_argument(
        "-r", "--repetir",
        type=int,
        default=1,
        metavar="N",
        help="Repetir a rolagem N vezes (padrão: 1)"
    )

    parser.add_argument(
        "-v", "--versao",
        action="version",
        version="Dice Roller 1.0"
    )

    args = parser.parse_args()

    if not args.expression:
        parser.print_help()
        sys.exit(1)

    if args.repetir < 1:
        print("Erro: --repetir deve ser maior que zero.")
        sys.exit(1)

    roller = DiceRoller()

    try:
        for i in range(args.repetir):
            if args.repetir > 1:
                print(f"\n{'='*20} ROLAGEM {i+1}/{args.repetir} {'='*20}")
            result = roller.roll(args.expression)
            print(roller.format_output(result))
    except ValueError as e:
        print(f"[ERRO] Erro: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nInterrompido pelo usuário.")
        sys.exit(0)


if __name__ == "__main__":
    main()