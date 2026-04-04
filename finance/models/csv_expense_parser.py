from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from typing import Dict, List
import csv
import re

from .parsed_expense import ParsedExpense


@dataclass
class CsvExpenseParser:
    @staticmethod
    def clean_description(description: str) -> str:
        if not description:
            return ""
        return (
            description.replace('"', "")
            .replace("'", "")
            .replace('"', "")
            .replace("\\", "")
            .strip()
        )

    @staticmethod
    def _normalize(s: str) -> str:
        return (
            s.replace("\ufeff", "").replace('"', "").replace(",", "").replace(" ", "")
        )

    def parse(self, csv_text: str) -> List[ParsedExpense]:
        expenses: List[ParsedExpense] = []
        lines = csv_text.split("\n")

        header_pattern = re.compile(
            r"תאריך\s*עסק[אה]?\s*שם\s*בית\s*העסק\s*סכום\s*[הח]?עסקה"
        )
        preferred_header_pattern = re.compile(
            r"תאריך\s*עסק[אה]?\s*שם\s*בית\s*העסק.*סכום\s*חיוב"
        )

        header_idx = -1
        column_map: Dict[str, int] = {"date": 0, "desc": 1, "amount": 2}
        preferred_header_idx = -1

        for i, line in enumerate(lines):
            normalized = self._normalize(line)
            if preferred_header_pattern.search(normalized):
                preferred_header_idx = i
                break

        if preferred_header_idx == -1:
            for i, line in enumerate(lines):
                normalized = self._normalize(line)
                if header_pattern.search(normalized):
                    preferred_header_idx = i
                    break

        if preferred_header_idx != -1:
            header_idx = preferred_header_idx
            line = lines[header_idx]
            parts = line.replace("\ufeff", "").split(",")
            parts = [p.strip() for p in parts]

            for idx, header in enumerate(parts):
                header_clean = header.strip().replace('"', "")
                if "תאריך" in header_clean and "עסקה" in header_clean:
                    column_map["date"] = idx
                elif "שם בית העסק" in header_clean:
                    column_map["desc"] = idx
                elif "סכום חיוב" in header_clean:
                    column_map["amount"] = idx
                elif "סכום העסקה" in header_clean:
                    column_map["amount"] = idx

        if header_idx == -1:
            date_regex = re.compile(r"\d{2}[/.]\d{2}[/.]\d{2,4}")
            for i, line in enumerate(lines):
                if date_regex.search(line):
                    header_idx = i - 1 if i > 0 else 0
                    break
            if header_idx < 0:
                header_idx = 0

        for i in range(header_idx + 1, len(lines)):
            raw_line = lines[i].strip()
            if not raw_line or 'סה"כ' in raw_line or 'סה"כ' in raw_line:
                continue

            try:
                reader = csv.reader(StringIO(raw_line))
                parts = next(reader)
            except Exception:
                parts = raw_line.split(",")

            if len(parts) < 3:
                continue

            date_idx = column_map.get("date", 0)
            if date_idx >= len(parts):
                continue
            date_str = parts[date_idx].strip()

            # Allow common formats: dd/mm/yyyy, dd.mm.yyyy, dd/mm/yy, ISO yyyy-mm-dd.
            if "/" not in date_str and "." not in date_str and "-" not in date_str:
                continue

            desc_idx = column_map.get("desc", 1)
            if desc_idx >= len(parts):
                continue
            description = self.clean_description(parts[desc_idx])

            if description and re.match(r"^\d{1,2}:\d{2}$", description.strip()):
                for alt_idx in range(desc_idx + 1, min(desc_idx + 3, len(parts))):
                    alt_desc = self.clean_description(parts[alt_idx])
                    if alt_desc and not re.match(r"^\d{1,2}:\d{2}$", alt_desc.strip()):
                        description = alt_desc
                        break
                else:
                    continue

            if not description:
                continue

            amount = None
            amount_idx = column_map.get("amount", len(parts) - 1)

            for idx in range(len(parts) - 1, max(0, len(parts) - 3), -1):
                cell = parts[idx].strip() if idx < len(parts) else ""
                if not cell:
                    continue

                amount_clean = (
                    cell.replace('"', "")
                    .replace(",", "")
                    .replace(" ", "")
                    .replace("=", "")
                )
                if not amount_clean:
                    continue

                try:
                    amount_value = float(amount_clean)
                    amount = -abs(amount_value)
                    break
                except ValueError:
                    continue

            if amount is None:
                if amount_idx < len(parts):
                    amount_str = (
                        parts[amount_idx]
                        .strip()
                        .replace('"', "")
                        .replace(",", "")
                        .replace(" ", "")
                        .replace("=", "")
                    )
                    try:
                        amount = -abs(float(amount_str))
                    except ValueError:
                        continue
                else:
                    continue

            expenses.append(
                ParsedExpense(date=date_str, description=description, amount=amount)
            )

        return expenses
