import datetime

import config
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import sqlite3
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.image as image

import numpy as np


def main():
    # Set up Database
    db_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'tarock.db')
    connection = sqlite3.connect(db_dir, check_same_thread=False)
    cursor = connection.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS Spiele (
        datum TEXT PRIMARY KEY,
        Andi float,
        Mama float,
        Markus float,
        Papa float
    );""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS Gesamtstand (
            name TEXT PRIMARY KEY,
            wert float
        );""")
    cursor.executemany("""
    INSERT OR IGNORE INTO Gesamtstand(name, wert) VALUES (?, ?);
    """,
                       [('Andi', 0.0), ('Mama', 0.0), ('Papa', 0.0), ('Markus', 0.0)])
    connection.commit()
    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS update_total_insert 
        AFTER INSERT ON Spiele
    BEGIN
        UPDATE Gesamtstand SET wert = wert + new.Andi WHERE name == 'Andi';
        UPDATE Gesamtstand SET wert = wert + new.Papa WHERE name == 'Papa';
        UPDATE Gesamtstand SET wert = wert + new.Mama WHERE name == 'Mama';
        UPDATE Gesamtstand SET wert = wert + new.Markus WHERE name == 'Markus';
    END;
    """)
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS update_total_delete 
            AFTER DELETE ON Spiele
        BEGIN
            UPDATE Gesamtstand SET wert = wert - old.Andi WHERE name == 'Andi';
            UPDATE Gesamtstand SET wert = wert - old.Papa WHERE name == 'Papa';
            UPDATE Gesamtstand SET wert = wert - old.Mama WHERE name == 'Mama';
            UPDATE Gesamtstand SET wert = wert - old.Markus WHERE name == 'Markus';
        END;
        """)
    cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_total_update 
                AFTER UPDATE ON Spiele
            BEGIN
                UPDATE Gesamtstand SET wert = wert - old.Andi + new.Andi WHERE name == 'Andi';
                UPDATE Gesamtstand SET wert = wert - old.Papa + new.Papa WHERE name == 'Papa';
                UPDATE Gesamtstand SET wert = wert - old.Mama + new.Mama WHERE name == 'Mama';
                UPDATE Gesamtstand SET wert = wert - old.Markus + new.Markus WHERE name == 'Markus';
            END;
            """)
    connection.commit()

    pic_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'plot.jpg')

    def start_command(update: Update, context: CallbackContext) -> None:
        update.message.reply_text("Ich verwalte und visualisiere Buchners Tarock Spielstände.")

    def help_command(update: Update, context: CallbackContext) -> None:
        help_text = "Wenn du ein neues Spiel zur Aufzeichnung hinzufügen möchtest, " \
                    "dann gib deine Nachricht im folgenden Format ein:\n" \
                    "Spiel 01.04.2021\n" \
                    "Andi 10.25\n" \
                    "Mama 12.8\n" \
                    "Papa -12.8\n" \
                    "Markus -10.25\n" \
                    "\n" \
                    "Man kann auch ein Spiel updaten mittels Update... statt Spiel...\n" \
                    "\n" \
                    "Wenn du ein Spiel löschen möchtest gib Delete 01.04.2021 ein (Datum anpassen)" \
                    "\n\n\n" \
                    "Wenn du den aktuellen Gesamtstand wissen möchtest dann gib einfach \"Gesamt\" ein\n" \
                    "\n\n\n" \
                    "Wenn du den alle einzelnen Spiele sehen möchtest gib \"Spiele\" ein\n" \
                    "\n\n\n" \
                    "Wenn du den Verlauf eines Spielers grafisch visualisiert haben möchtest dann schreibe einfach den" \
                    " Namen des Spielers (Andi, Markus, Mama oder Papa)\n" \
                    "\n\n\n" \
                    "Du kannst auch das Verhältnis mehrerer Spielverläufe visualisieren lassen: \n" \
                    "\"Mama - Markus\" oder \"Mama - Markus - Papa\" oder einfach \"Alle\""
        update.message.reply_text(help_text)

    def get_total() -> str:
        result = ""
        total = cursor.execute("SELECT * FROM Gesamtstand").fetchall()

        for t in total:
            result += f"\n{t[0]} {t[1]}"

        return result

    def get_all_games() -> str:
        result = "Spiele:"
        total = cursor.execute("SELECT * FROM Spiele").fetchall()

        for t in total:
            result += f"\n\n{t[0]}: Andi: {t[1]}, Mama {t[2]}, Markus {t[3]}, Papa {t[4]}"

        return result

    def process_new_game(text) -> str:
        lines = text.splitlines()
        if len(lines) != 5:
            return "Unpassende Anzahl an Einträgen"

        try:
            date = lines[0][6:]
            # convert into both directions to check format
            date = datetime.datetime.strptime(date, "%d.%m.%Y")
            date = datetime.datetime.strftime(date, "%d.%m.%Y")
        except ValueError:
            return "Datum hat falsches Format, sollte dd.mm.yyyy sein."
        lines = lines[1:]
        andi, markus, mama, papa = None, None, None, None
        for line in lines:
            try:
                if line.upper().startswith("andi".upper()):
                    andi = float(line[5:])
                elif line.upper().startswith("mama".upper()):
                    mama = float(line[5:])
                elif line.upper().startswith("papa".upper()):
                    papa = float(line[5:])
                elif line.upper().startswith("markus".upper()):
                    markus = float(line[7:])
                else:
                    return "Konnte eine Zeile nicht identifizieren"
            except ValueError:
                return "Mindestens ein Wert fehlt oder hat falsche Format"
        if None in [andi, markus, mama, papa]:
            return "Es wurden nicht alle Spieler genannt (Andi, Mama, Papa, Markus)"

        if mama + markus + andi + papa != 0:
            return f"Die Summe der Spielstände ist nicht 0 (Buchhaltung by Markus?)" \
                   f"\n{andi} + {markus} + {mama} + {papa} = {andi + markus + mama + papa}\n" \
                   f"Probiers nochmal mit einem Korrekturfaktor wenns sein muss"
        try:
            cursor.execute("""
                    INSERT INTO Spiele(datum, Andi, Mama, Markus, Papa) VALUES (?,?,?,?,?)
                    """, (date, andi, mama, markus, papa))
        except sqlite3.IntegrityError:
            return f"Am {date} existiert bereits ein Spiel... ihr spielt sicher nicht zwei mal am Tag"
        connection.commit()
        return f"Habe das Spiel am {date} eingefügt:\nAndi: {andi}\nMama: {mama}\nMarkus: {markus}\nPapa: {papa}"

    def update_game(text) -> str:
        lines = text.splitlines()
        if len(lines) != 5:
            return "Unpassende Anzahl an Einträgen"

        try:
            date = lines[0][7:]
            # convert into both directions to check format
            date = datetime.datetime.strptime(date, "%d.%m.%Y")
            date = datetime.datetime.strftime(date, "%d.%m.%Y")
        except ValueError:
            return "Datum hat falsches Format, sollte dd.mm.yyyy sein."
        lines = lines[1:]
        andi, markus, mama, papa = None, None, None, None
        for line in lines:
            try:
                if line.upper().startswith("andi".upper()):
                    andi = float(line[5:])
                elif line.upper().startswith("mama".upper()):
                    mama = float(line[5:])
                elif line.upper().startswith("papa".upper()):
                    papa = float(line[5:])
                elif line.upper().startswith("markus".upper()):
                    markus = float(line[7:])
                else:
                    return "Konnte eine Zeile nicht identifizieren"
            except ValueError:
                return "Mindestens ein Wert fehlt oder hat falsche Format"
        if None in [andi, markus, mama, papa]:
            return "Es wurden nicht alle Spieler genannt (Andi, Mama, Papa, Markus)"

        if mama + markus + andi + papa != 0:
            return f"Die Summe der Spielstände ist nicht 0 (Buchhaltung by Markus?)" \
                   f"\n{andi} + {markus} + {mama} + {papa} = {andi + markus + mama + papa}\n" \
                   f"Probiers nochmal mit einem Korrekturfaktor wenns sein muss"
        cursor.execute("""
                        UPDATE Spiele SET Andi = ?, Mama = ?, Markus = ?,  Papa = ? WHERE datum = ?
                        """, (andi, mama, markus, papa, date))
        connection.commit()
        return f"Habe das Spiel am {date} sofern es existiert upgedated:" \
               f"\nAndi: {andi}\nMama: {mama}\nMarkus: {markus}\nPapa: {papa}"

    def delete_game(text) -> str:
        try:
            date = text[7:]
            # convert into both directions to check format
            date = datetime.datetime.strptime(date, "%d.%m.%Y")
            date = datetime.datetime.strftime(date, "%d.%m.%Y")
        except ValueError:
            return "Datum hat falsches Format, sollte dd.mm.yyyy sein."

        cursor.execute("""
                        DELETE FROM Spiele WHERE datum = ?;
                        """, (date,))
        connection.commit()
        return f"Habe das Spiel am {date} gelöscht"

    def parse_for_plot(text, update) -> None:
        if text.upper().startswith("Andi".upper()):
            ...
        elif text.upper().startswith("Markus".upper()):
            ...
        elif text.upper().startswith("Mama".upper()):
            ...
        elif text.upper().startswith("Papa".upper()):
            ...
        else:
            update.message.reply_text("Unbekanntes Format")

        mama, papa, andi, markus = False, False, False, False
        if "Andi".upper() in text.upper():
            andi = True
        if "Markus".upper() in text.upper():
            markus = True
        if "Mama".upper() in text.upper():
            mama = True
        if "Papa".upper() in text.upper():
            papa = True

        generate_plot(andi=andi, markus=markus, mama=mama, papa=papa)
        try:
            pic = open(pic_dir, 'rb')
        except IOError:
            update.message.reply_text("Das Bild kann ich irgendwie grad nicht finden, frag Andi was los ist")
            return
        update.message.reply_photo(pic)
        pic.close()

    def generate_plot(andi=False, markus=False, mama=False, papa=False):
        fig, ax = plt.subplots(1, 1, figsize=(16, 9), dpi=80)
        entries = cursor.execute("SELECT * FROM Spiele").fetchall()
        dates = [d[0] for d in entries]
        upper, lower = 0.0, 0.0
        if andi:
            andi_y = [d[1] for d in entries]
            current = 0
            tmp = []
            for x in andi_y:
                tmp.append(current+x)
                current += x
            andi_y = tmp
            if max(andi_y) > upper:
                upper = max(andi_y)
            if min(andi_y) < lower:
                lower = min(andi_y)
            ax.fill_between(dates, y1=andi_y, y2=0, label='Andi',
                            alpha=0.5, color='tab:blue', linewidth=2)
        if mama:
            mama_y = [d[2] for d in entries]
            current = 0
            tmp = []
            for x in mama_y:
                tmp.append(current + x)
                current += x
            mama_y = tmp
            if max(mama_y) > upper:
                upper = max(mama_y)
            if min(mama_y) < lower:
                lower = min(mama_y)
            ax.fill_between(dates, y1=mama_y, y2=0, label='Mama',
                            alpha=0.5, color='tab:red', linewidth=2)
        if markus:
            markus_y = [d[3] for d in entries]
            current = 0
            tmp = []
            for x in markus_y:
                tmp.append(current + x)
                current += x
            markus_y = tmp
            if max(markus_y) > upper:
                upper = max(markus_y)
            if min(markus_y) < lower:
                lower = min(markus_y)
            ax.fill_between(dates, y1=markus_y, y2=0, label='Markus',
                            alpha=0.5, color='tab:green', linewidth=2)
        if papa:
            papa_y = [d[4] for d in entries]
            current = 0
            tmp = []
            for x in papa_y:
                tmp.append(current + x)
                current += x
            papa_y = tmp
            if max(papa_y) > upper:
                upper = max(papa_y)
            if min(papa_y) < lower:
                lower = min(papa_y)
            ax.fill_between(dates, y1=papa_y, y2=0, label='Papa',
                            alpha=0.5, color='tab:brown', linewidth=2)


        # Decorations
        ax.set_title('Spielverlauf', fontsize=18)
        upper = round(upper * 1.01, 2)
        lower = round(lower * 0.99, 2)
        y_ticks = np.arange(lower,
                            upper,
                            round(np.divide(upper - lower, 10), 2))
        ax.set(ylim=[y_ticks[0], y_ticks[-1]])
        ax.legend(loc='best', fontsize=12)
        label_ten_ticks = round(len(dates) / 10)  # label around 10 ticks every time it's plotted
        if label_ten_ticks == 0:
            label_ten_ticks = 1
        plt.xticks(range(0, len(dates), label_ten_ticks), dates[::label_ten_ticks], fontsize=10,
                   horizontalalignment='center')
        plt.yticks(y_ticks, fontsize=10)
        plt.xlim(0, dates[-1])
        plt.xlabel('Datum')
        plt.ylabel('Guthaben')

        # Draw Tick lines
        for y in y_ticks:
            plt.hlines(y, xmin=0, xmax=len(dates), colors='black', alpha=0.3, linestyles="--", lw=0.5)

        # Lighten borders
        plt.gca().spines["top"].set_alpha(0)
        plt.gca().spines["bottom"].set_alpha(.3)
        plt.gca().spines["right"].set_alpha(0)
        plt.gca().spines["left"].set_alpha(.3)

        plt.ylim(lower, upper)
        plt.savefig(
            pic_dir,
            format='jpg'
        )


    def answer(update: Update, context: CallbackContext) -> None:
        if update.message.text.upper() == "Hilfe".upper():
            help_command(update, context)
            return
        if update.message.text.upper().startswith("Spiele".upper()):
            update.message.reply_text(get_all_games())
            return
        if update.message.text.upper().startswith("Spiel".upper()):
            update.message.reply_text(process_new_game(update.message.text))
            return
        if update.message.text.upper() == "Gesamt".upper():
            update.message.reply_text(get_total())
            return
        if update.message.text.upper().startswith("Update".upper()):
            update.message.reply_text(update_game(update.message.text))
            return
        if update.message.text.upper().startswith("Delete".upper()):
            update.message.reply_text(delete_game(update.message.text))
            return
        if update.message.text.upper().startswith("Alle".upper()):
            parse_for_plot("Andi-Mama-Markus_Papa", update)
            return
        parse_for_plot(update.message.text, update)

    updater = Updater(config.bot_token)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start_command))
    dispatcher.add_handler(CommandHandler("help", help_command))

    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, answer))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
