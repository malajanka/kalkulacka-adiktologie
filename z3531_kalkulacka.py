# /// script
# requires-python = ">=3.10"
# dependencies = ["marimo", "altair", "pandas"]
# ///
"""RATIO – kalkulačka k programu Z3531 (protidrogová politika), návrh SR 2027.

Spuštění jako aplikace (bez kódu):   marimo run z3531_kalkulacka.py
Úpravy:                              marimo edit z3531_kalkulacka.py
Export do jednoho HTML (běží v prohlížeči):
    marimo export html-wasm z3531_kalkulacka.py -o web --mode run
"""

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium", app_title="Z3531 – kalkulačka")


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import pandas as pd
    import altair as alt

    CYAN = "#9ADBDA"    # RATIO TORP Cyan – nominální částky
    PURPLE = "#2C143E"  # RATIO Deep Purple – reálná hodnota
    AMBER = "#FDC940"   # RATIO Amber – jen zvýraznění
    SILVER = "#ECECEC"

    def kc(x, des=0):
        """Formát čísla po česku: mezera jako oddělovač tisíců, desetinná čárka."""
        s = f"{x:,.{des}f}".replace(",", " ").replace(".", ",")
        return s

    return AMBER, CYAN, PURPLE, SILVER, alt, kc, mo, pd


@app.cell(hide_code=True)
def _():
    # ---------------------------------------------------------------
    # DATA – vše z primárních zdrojů ve složce financovani_sluzeb/
    # ---------------------------------------------------------------
    # Program protidrogové politiky (2024–2026 Z0407 u ÚV, od 2027 Z3531 u MZd), mil. Kč
    # 2024, 2025: VZ RVKPZ 2024/2025, tab. 7-1; 2026: zákon 38/2026 Sb. + seznam dotací MZd;
    # 2027–2029: H_01 SR 2027, s. 7 (shodně 415 na všechny tři roky)
    PROGRAM = {2024: 315, 2025: 415, 2026: 415, 2027: 415, 2028: 415, 2029: 415}

    # Požadavky žadatelů v dotačním řízení, mil. Kč (VZ RVKPZ 2024/2025, tab. 7-1, 7-2)
    POZADAVKY = {2024: 470.7, 2025: 555.9}

    # Průměrná míra inflace, % (MF ČR: D_01 SR 2027 a K_01 SDV 2028–2029, makro tabulka)
    # 2024–2025 skutečnost, 2026–2027 predikce, 2028–2029 výhled
    INFLACE = {2024: 2.4, 2025: 2.5, 2026: 2.2, 2027: 2.7, 2028: 2.3, 2029: 2.3}

    # Růst průměrné mzdy, %
    # 2026, 2027: MF ČR (D_01, tab. 2.1 „Prům. mzda“)
    # 2025, 2028, 2029: ODVOZENO = růst objemu mezd a platů − růst zaměstnanosti (MF, K_01)
    MZDY = {2025: 6.0, 2026: 7.6, 2027: 6.2, 2028: 5.3, 2029: 4.6}
    MZDY_ODVOZENE = {2025, 2028, 2029}

    # Příjmy státního rozpočtu z návykových produktů 2027, mld. Kč (E_01, K_01)
    PRIJMY_2027 = {
        "Spotřební daň z tabáku a souvisejících výrobků": 63.3,
        "Daň z hazardních her (podíl SR)": 16.8,
        "Spotřební daň z lihu": 8.9,
        "Spotřební daň z piva": 4.2,
        "Spotřební daň z vína": 0.5,
        "Spotřební daň z kratomu (nová)": 0.3,
    }

    # Veřejné výdaje na celou síť adiktologických služeb 2024, mil. Kč (Souhrnná zpráva o závislostech 2025, kap. 2.9)
    VEREJNE_VYDAJE_2024 = 1631.6

    ZAKLADNI_ROK = 2025
    return (
        INFLACE,
        MZDY,
        MZDY_ODVOZENE,
        POZADAVKY,
        PRIJMY_2027,
        PROGRAM,
        VEREJNE_VYDAJE_2024,
        ZAKLADNI_ROK,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        """
        # Program Z3531 v návrhu rozpočtu 2027

        Program protidrogové politiky (**Z3531**, od roku 2027 v kapitole MZd) má v návrhu
        státního rozpočtu na rok 2027 i ve střednědobém výhledu **415 mil. Kč na každý rok
        2027, 2028 i 2029**. Stejnou částku dostal už v letech 2025 a 2026.
        Kalkulačka ukazuje, co to znamená v reálných penězích a jak daleko je to od potřeby.

        Všechna čísla pocházejí z návrhu SR 2027, střednědobého výhledu a výročních zpráv RVKPZ.
        Zdroje jsou uvedené dole.
        """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    meritko = mo.ui.radio(
        options={
            "spotřebitelských cen (inflace)": "ceny",
            "mezd (služby platí hlavně lidi)": "mzdy",
        },
        value="mezd (služby platí hlavně lidi)",
        label="**Přepočítat podle růstu**",
    )
    odchylka = mo.ui.slider(
        start=-1.0,
        stop=2.0,
        step=0.1,
        value=0.0,
        show_value=True,
        label="**Odchylka od predikce MF** (p. b. ročně, 2026–2029)",
    )
    mo.vstack(
        [
            mo.md("## 1 · Reálná hodnota 2024–2029"),
            mo.hstack([meritko, odchylka], justify="start", gap=3, wrap=True),
        ]
    )
    return meritko, odchylka


@app.cell(hide_code=True)
def _(INFLACE, MZDY, PROGRAM, ZAKLADNI_ROK, meritko, odchylka):
    _rust = INFLACE if meritko.value == "ceny" else MZDY

    # Cenový/mzdový index se základem 2025 = 1
    index = {ZAKLADNI_ROK: 1.0}
    index[2024] = 1.0 / (1 + _rust[2025] / 100)
    for _r in range(2026, 2030):
        index[_r] = index[_r - 1] * (1 + (_rust[_r] + odchylka.value) / 100)

    realne = {r: PROGRAM[r] / index[r] for r in PROGRAM}
    udrzeni = {r: PROGRAM[ZAKLADNI_ROK] * index[r] for r in range(2026, 2030)}
    ztrata_kumul = sum(udrzeni[r] - PROGRAM[r] for r in udrzeni)
    return index, realne, udrzeni, ztrata_kumul


@app.cell(hide_code=True)
def _(CYAN, PROGRAM, PURPLE, alt, kc, meritko, pd, realne):
    _nom_lbl = "Nominálně (návrh rozpočtu)"
    _real_lbl = "Reálně, v hodnotě roku 2025"
    _df = pd.DataFrame(
        [
            {"rok": str(r), "řada": _nom_lbl, "mil": PROGRAM[r], "popis": f"{kc(PROGRAM[r])} mil. Kč"}
            for r in PROGRAM
        ]
        + [
            {"rok": str(r), "řada": _real_lbl, "mil": round(realne[r], 1), "popis": f"{kc(realne[r])} mil. Kč"}
            for r in PROGRAM
        ]
    )
    _barvy = alt.Scale(domain=[_nom_lbl, _real_lbl], range=[CYAN, PURPLE])
    _zaklad = alt.Chart(_df).encode(
        x=alt.X("rok:N", title=None, axis=alt.Axis(labelAngle=0, labelFontSize=13)),
        y=alt.Y("mil:Q", title="mil. Kč", scale=alt.Scale(domain=[0, 450]),
                axis=alt.Axis(grid=True, gridColor="#e6e6e6", tickCount=5)),
        color=alt.Color("řada:N", scale=_barvy, title=None,
                        legend=alt.Legend(orient="top", labelFontSize=13, symbolSize=160, labelLimit=0)),
        tooltip=[alt.Tooltip("rok:N", title="Rok"), alt.Tooltip("řada:N", title="Řada"),
                 alt.Tooltip("popis:N", title="Částka")],
    )
    _sloupce = _zaklad.transform_filter(alt.datum["řada"] == _nom_lbl).mark_bar(
        cornerRadiusTopLeft=4, cornerRadiusTopRight=4, width=46
    )
    _linka = _zaklad.transform_filter(alt.datum["řada"] == _real_lbl).mark_line(
        strokeWidth=2.5, point=alt.OverlayMarkDef(size=90, filled=True, stroke="white", strokeWidth=2)
    )
    _popisky = (
        alt.Chart(_df[_df["řada"] == _real_lbl])
        .mark_text(dy=-14, fontSize=12, fontWeight="bold", color=PURPLE)
        .encode(x="rok:N", y="mil:Q", text=alt.Text("mil:Q", format=".0f"))
    )
    graf_realne = (
        (_sloupce + _linka + _popisky)
        .properties(height=340, width="container",
                    title=alt.Title(
                        "Program Z3531 nominálně a reálně",
                        subtitle=f"Reálná hodnota přepočtená podle růstu {'cen' if meritko.value == 'ceny' else 'mezd'}, základ 2025",
                        anchor="start", fontSize=15, subtitleFontSize=12))
        .configure_view(strokeWidth=0)
        .configure(font="PT Sans")
        .configure_axis(domainColor="#999", labelColor="#333", titleColor="#555")
    )
    graf_realne
    return


@app.cell(hide_code=True)
def _(PROGRAM, kc, meritko, mo, realne, udrzeni, ztrata_kumul):
    _co = "cen" if meritko.value == "ceny" else "mezd"
    _ztrata_2029 = PROGRAM[2025] - realne[2029]
    mo.vstack(
        [
            mo.hstack(
                [
                    mo.stat(
                        value=f"{kc(realne[2029])} mil.",
                        label="Reálná hodnota v roce 2029",
                        caption=f"o {kc(_ztrata_2029)} mil. Kč méně než v roce 2025",
                        bordered=True,
                    ),
                    mo.stat(
                        value=f"{kc(udrzeni[2029])} mil.",
                        label="Potřeba v roce 2029 pro udržení úrovně 2025",
                        caption=f"valorizace podle růstu {_co}",
                        bordered=True,
                    ),
                    mo.stat(
                        value=f"{kc(ztrata_kumul)} mil.",
                        label="Chybí služby za roky 2026–2029 celkem",
                        caption="součet ročních rozdílů proti valorizaci",
                        bordered=True,
                    ),
                ],
                widths="equal",
                gap=1,
                wrap=True,
            ),
            mo.md(
                f"""
                Kdyby program v letech 2026–2029 rostl jen tak, aby udržel hodnotu roku 2025,
                potřeboval by v roce 2027 **{kc(udrzeni[2027])} mil. Kč** a v roce 2029
                **{kc(udrzeni[2029])} mil. Kč**.
                Adiktologické služby jsou z velké části mzdové náklady, takže přepočet podle mezd
                lépe vystihuje, kolik práce za peníze služby reálně zaplatí.
                """
            ),
        ]
    )
    return


@app.cell(hide_code=True)
def _(MZDY_ODVOZENE, meritko, mo):
    _pozn = (
        "Růst mezd: MF ČR pro 2026 (7,6 %) a 2027 (6,2 %). Roky "
        + ", ".join(str(r) for r in sorted(MZDY_ODVOZENE))
        + " jsou odvozené jako růst objemu mezd a platů minus růst zaměstnanosti z makrorámce MF."
        if meritko.value == "mzdy"
        else "Inflace: MF ČR, průměrná míra inflace (2026–2027 predikce, 2028–2029 výhled)."
    )
    mo.callout(mo.md(f"<small>{_pozn}</small>"), kind="neutral")
    return


@app.cell(hide_code=True)
def _():
    # Skutečné rozdělení programu v roce 2025 podle typu služby, mil. Kč
    # (VZ RVKPZ 2025, tab. 7-1 + 7-2, součet obou výzev; zaokrouhleno na celé mil.)
    SIT = {
        "prevence": ("Preventivní služby", 31, 44),
        "hr": ("Minimalizace rizik (harm reduction)", 153, 208),
        "ambulance": ("Ambulantní léčba a poradenství", 124, 167),
        "rezidencni": ("Rezidenční léčba", 44, 53),
        "nasledna": ("Následná péče", 26, 37),
        "ivh": ("Informační, výzkumné a síťovací projekty", 37, 47),
    }
    # (klíč: název, skutečnost 2025 dotace, požadavek žadatelů 2025)

    # Priority rozvoje z výzvy MZd na rok 2027 (čl. 3, dotační oblast I), schválené
    # usnesením vlády č. 609/2026 – platí „v případě, že objem alokovaných prostředků
    # umožní rozvoj sítě“
    ROZVOJ = {
        "kapacity": ("Rozšíření ambulancí a substituční léčby",
                     "nové úvazky v přímé péči (min. +1,0 úvazku na službu)"),
        "testovani": ("Testování na infekční nemoci",
                      "HIV, HCV, syfilis u lidí, kteří užívají drogy rizikově"),
        "inovace_hr": ("Inovativní harm reduction",
                       "naloxon, bezpečná aplikace, nízkoprahová psychiatrická péče"),
        "prevence_rozvoj": ("Indikovaná a selektivní prevence",
                            "rozvoj preventivních služeb pro ohrožené skupiny"),
        "digital": ("Digitální závislosti",
                    "nové programy léčby a poradenství"),
        "stabilizace": ("Krátkodobá krizová stabilizace",
                        "pilotní lůžka krizové stabilizace pro lidi se závislostí"),
    }
    return ROZVOJ, SIT


@app.cell(hide_code=True)
def _(mo):
    vychozi = mo.ui.radio(
        options={"skutečnost 2025 (415 mil.)": "dotace",
                 "požadavky žadatelů 2025 (556 mil.)": "pozadavky"},
        value="skutečnost 2025 (415 mil.)",
        label="**Stávající síť nastavit podle**",
    )
    mo.vstack(
        [
            mo.md(
                """
                ## 2 · Rozdělení podle služeb a priority 2027

                Posuvníky v levém sloupci ukazují, jak se program v roce 2025 rozdělil mezi typy služeb.
                V pravém sloupci jsou priority rozvoje, které vláda schválila do výzvy na rok 2027
                (usnesení č. 609/2026). Výzva je ovšem podmiňuje tím, že „objem alokovaných finančních
                prostředků umožní rozvoj sítě“. Při 415 mil. Kč na ně nezbývá nic, proto začínají na nule.
                Nastavte, kolik by podle vás potřebovaly.
                """
            ),
            vychozi,
        ]
    )
    return (vychozi,)


@app.cell(hide_code=True)
def _(PROGRAM, ROZVOJ, SIT, kc, mo, udrzeni, vychozi):
    _i = 1 if vychozi.value == "dotace" else 2
    sit = mo.ui.dictionary(
        {k: mo.ui.slider(start=0, stop=300, step=1, value=v[_i], show_value=True,
                         label=v[0], full_width=True) for k, v in SIT.items()}
    )
    rozvoj = mo.ui.dictionary(
        {k: mo.ui.slider(start=0, stop=200, step=5, value=0, show_value=True,
                         label=v[0], full_width=True) for k, v in ROZVOJ.items()}
    )
    _valorizace_2027 = max(0.0, udrzeni[2027] - PROGRAM[2027])
    valorizace = mo.ui.checkbox(
        value=True,
        label=f"Přičíst valorizaci stávající sítě na rok 2027 (+{kc(_valorizace_2027)} mil. Kč podle části 1)",
    )
    mo.vstack(
        [
            mo.hstack(
                [
                    mo.vstack([mo.md("**Stávající síť** (mil. Kč)")] + [sit[k] for k in SIT], gap=0.6),
                    mo.vstack(
                        [mo.md("**Rozvoj slíbený ve výzvě 2027** (mil. Kč)")]
                        + [mo.vstack([rozvoj[k], mo.md(f"<small>{ROZVOJ[k][1]}</small>")], gap=0)
                           for k in ROZVOJ],
                        gap=0.6,
                    ),
                ],
                widths="equal", gap=2, wrap=True, align="start",
            ),
            valorizace,
        ],
        gap=1,
    )
    return rozvoj, sit, valorizace


@app.cell(hide_code=True)
def _(
    AMBER,
    CYAN,
    POZADAVKY,
    PRIJMY_2027,
    PROGRAM,
    PURPLE,
    ROZVOJ,
    SIT,
    alt,
    kc,
    mo,
    pd,
    rozvoj,
    sit,
    udrzeni,
    valorizace,
):
    _val = max(0.0, udrzeni[2027] - PROGRAM[2027]) if valorizace.value else 0.0
    _sit_sum = sum(sit.value.values())
    _rozvoj_sum = sum(rozvoj.value.values())
    navrh_celkem = _sit_sum + _rozvoj_sum + _val
    _prijmy = sum(PRIJMY_2027.values()) * 1000

    # Graf 1: rozdělení podle položek
    _S, _R, _T = "Stávající síť", "Rozvoj slíbený ve výzvě 2027", "Skutečnost 2025"
    _rows = [{"položka": SIT[k][0], "řada": _S, "mil": sit.value[k]} for k in SIT]
    _rows += [{"položka": ROZVOJ[k][0], "řada": _R, "mil": rozvoj.value[k]} for k in ROZVOJ]
    if _val:
        _rows.append({"položka": "Valorizace mezd a nákladů", "řada": _S, "mil": round(_val)})
    _ticks = [{"položka": SIT[k][0], "řada": _T, "mil": SIT[k][1]} for k in SIT]
    _df = pd.DataFrame(_rows + _ticks)
    _df["popis"] = _df["mil"].map(lambda v: f"{kc(v)} mil. Kč")
    _poradi = [SIT[k][0] for k in SIT] + (["Valorizace mezd a nákladů"] if _val else []) + [ROZVOJ[k][0] for k in ROZVOJ]
    _barvy = alt.Scale(domain=[_S, _R, _T], range=[CYAN, AMBER, PURPLE])
    _base = alt.Chart(_df).encode(
        y=alt.Y("položka:N", sort=_poradi, title=None, axis=alt.Axis(labelFontSize=12, labelLimit=280)),
        x=alt.X("mil:Q", title="mil. Kč", scale=alt.Scale(domain=[0, 300]),
                axis=alt.Axis(grid=True, gridColor="#e6e6e6")),
        color=alt.Color("řada:N", scale=_barvy, title=None,
                        legend=alt.Legend(orient="top", labelFontSize=13, labelLimit=0)),
        tooltip=[alt.Tooltip("položka:N", title="Položka"), alt.Tooltip("řada:N", title="Řada"),
                 alt.Tooltip("popis:N", title="Částka")],
    )
    _graf_polozky = (
        (
            _base.transform_filter(alt.datum["řada"] != _T).mark_bar(
                cornerRadiusTopRight=4, cornerRadiusBottomRight=4, height=18)
            + _base.transform_filter(alt.datum["řada"] == _T).mark_tick(thickness=3, size=26, opacity=1)
        )
        .properties(height=440, width="container",
                    title=alt.Title("Váš návrh podle položek",
                                    subtitle="Svislá čárka = skutečné rozdělení v roce 2025",
                                    anchor="start", fontSize=15, subtitleFontSize=12))
        .configure_view(strokeWidth=0)
        .configure(font="PT Sans")
        .configure_axis(domainColor="#999", labelColor="#333", titleColor="#555")
    )

    # Graf 2: přiděleno, požadováno, váš návrh
    _rows2 = [
        ("2024 · přiděleno", PROGRAM[2024], "přiděleno"),
        ("2024 · požadováno", POZADAVKY[2024], "požadováno"),
        ("2025 · přiděleno", PROGRAM[2025], "přiděleno"),
        ("2025 · požadováno", POZADAVKY[2025], "požadováno"),
        ("2027 · návrh SR", PROGRAM[2027], "přiděleno"),
        ("2027 · váš návrh", round(navrh_celkem, 1), "váš návrh"),
    ]
    _df2 = pd.DataFrame(_rows2, columns=["položka", "mil", "typ"])
    _df2["popis"] = _df2["mil"].map(lambda v: f"{kc(v, 1 if v % 1 else 0)} mil. Kč")
    _barvy2 = alt.Scale(domain=["přiděleno", "požadováno", "váš návrh"], range=[CYAN, "#B9C4C4", AMBER])
    _xmax = max(1500, navrh_celkem * 1.15)
    _base2 = alt.Chart(_df2).encode(
        y=alt.Y("položka:N", sort=None, title=None, axis=alt.Axis(labelFontSize=13, labelLimit=220)),
        x=alt.X("mil:Q", title="mil. Kč", scale=alt.Scale(domain=[0, _xmax]),
                axis=alt.Axis(grid=True, gridColor="#e6e6e6",
                              labelExpr="replace(format(datum.value, ','), ',', ' ')")),
    )
    _graf_celkem = (
        (
            _base2.mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4, height=26).encode(
                color=alt.Color("typ:N", scale=_barvy2, title=None,
                                legend=alt.Legend(orient="top", labelFontSize=13, labelLimit=0)),
                tooltip=[alt.Tooltip("položka:N", title="Položka"), alt.Tooltip("popis:N", title="Částka")],
            )
            + _base2.mark_text(align="left", dx=6, fontSize=12, color="#222").encode(text="popis:N")
        )
        .properties(height=280, width="container",
                    title=alt.Title("Přiděleno, požadováno a váš návrh",
                                    subtitle="Požadavky žadatelů podle výročních zpráv RVKPZ 2024 a 2025",
                                    anchor="start", fontSize=15, subtitleFontSize=12))
        .configure_view(strokeWidth=0)
        .configure(font="PT Sans")
        .configure_axis(domainColor="#999", labelColor="#333", titleColor="#555")
    )

    _rozdil = navrh_celkem - PROGRAM[2027]
    mo.vstack(
        [
            _graf_polozky,
            mo.hstack(
                [
                    mo.stat(value=f"{kc(navrh_celkem)} mil.", label="Váš návrh programu na rok 2027",
                            caption=f"síť {kc(_sit_sum)} + rozvoj {kc(_rozvoj_sum)} + valorizace {kc(_val)}",
                            bordered=True),
                    mo.stat(value=f"{'+' if _rozdil >= 0 else '−'}{kc(abs(_rozdil))} mil.",
                            label="Proti návrhu SR 2027 (415 mil.)",
                            caption=f"{kc(navrh_celkem / PROGRAM[2027], 2)}× částka v návrhu",
                            bordered=True),
                    mo.stat(value=f"{kc(navrh_celkem / _prijmy * 100, 2)} %",
                            label="Podíl na příjmech z návykových produktů",
                            caption="návrh SR 2027: 0,44 %",
                            bordered=True),
                ],
                widths="equal", gap=1, wrap=True,
            ),
            _graf_celkem,
            mo.md(
                f"""
                V roce 2025 žadatelé požadovali **{kc(POZADAVKY[2025], 1)} mil. Kč**, tedy o
                {kc(POZADAVKY[2025] - PROGRAM[2025], 1)} mil. víc, než program rozdělil, a to i přesto,
                že výzva sama omezuje, o kolik lze žádat. Odborníci z oboru odhadují, že k plnému
                pokrytí služeb chybí 600–800 mil. Kč ročně, tedy program kolem 1,0–1,2 mld. Kč.
                """
            ),
            mo.callout(
                mo.md(
                    "<small>**Co zaznělo v médiích:** premiér v srpnu 2026 navýšení prostředků na protidrogovou "
                    "politiku přislíbil, bez konkrétní částky. Po jednání vlády 21. 9. 2026 ČTK uvedla, že "
                    "„dalších 85 milionů korun poputuje na podporu prevence“. V návrhu státního rozpočtu "
                    "ani ve výzvě MZd na rok 2027 se tato částka zatím nepropsala.</small>"
                ),
                kind="neutral",
            ),
        ]
    )
    return (navrh_celkem,)


@app.cell(hide_code=True)
def _(PRIJMY_2027, PROGRAM, mo):
    prijmy_celkem = sum(PRIJMY_2027.values()) * 1000  # mil. Kč
    _soucasny_podil = PROGRAM[2027] / prijmy_celkem * 100
    podil = mo.ui.slider(
        start=0.2,
        stop=3.0,
        step=0.05,
        value=round(_soucasny_podil, 2),
        show_value=True,
        label="**Podíl příjmů z návykových produktů pro program Z3531** (%)",
    )
    mo.vstack(
        [
            mo.md(
                """
                ## 3 · Podíl na příjmech z návykových produktů

                Stát v roce 2027 podle návrhu rozpočtu vybere na spotřebních daních z tabáku, alkoholu
                a kratomu a na dani z hazardu přibližně **94 mld. Kč**. Jakou část by si zasloužily
                služby, které řeší dopady těchto produktů?
                """
            ),
            podil,
        ]
    )
    return podil, prijmy_celkem


@app.cell(hide_code=True)
def _(PROGRAM, VEREJNE_VYDAJE_2024, kc, mo, podil, prijmy_celkem):
    _castka = prijmy_celkem * podil.value / 100
    _halere_dnes = PROGRAM[2027] / prijmy_celkem * 100 * 100  # haléřů ze stokoruny
    mo.vstack(
        [
            mo.hstack(
                [
                    mo.stat(
                        value=f"{kc(prijmy_celkem / 1000, 1)} mld.",
                        label="Příjmy SR z návykových produktů 2027",
                        caption="tabák, líh, pivo, víno, kratom, hazard (podíl SR)",
                        bordered=True,
                    ),
                    mo.stat(
                        value=f"{kc(_halere_dnes)} haléřů",
                        label="Ze stokoruny těchto příjmů jde do Z3531",
                        caption=f"415 mil. Kč = {kc(PROGRAM[2027] / prijmy_celkem * 100, 2)} %",
                        bordered=True,
                    ),
                    mo.stat(
                        value=f"{kc(_castka)} mil.",
                        label=f"Program při podílu {kc(podil.value, 2)} %",
                        caption=f"{'+' if _castka >= PROGRAM[2027] else '−'}{kc(abs(_castka - PROGRAM[2027]))} mil. Kč proti návrhu",
                        bordered=True,
                    ),
                ],
                widths="equal",
                gap=1,
                wrap=True,
            ),
            mo.md(
                f"""
                Pro srovnání: veřejné rozpočty (stát, kraje a obce dohromady) daly v roce 2024 na celou síť
                adiktologických služeb {kc(VEREJNE_VYDAJE_2024 / 1000, 2)} mld. Kč, tedy necelá 2 % toho,
                co stát z návykových produktů vybere.
                """
            ),
        ]
    )
    return


@app.cell(hide_code=True)
def _(PROGRAM, kc, meritko, mo, realne, udrzeni):
    _co = "cen" if meritko.value == "ceny" else "mezd"
    mo.vstack(
        [
            mo.md("## Shrnutí"),
            mo.callout(
                mo.md(
                    f"Vláda navrhuje dát protidrogovým službám pět let po sobě stejných "
                    f"{kc(PROGRAM[2027])} mil. Kč. Po přepočtu na růst {_co} to v roce 2029 bude reálně "
                    f"jen **{kc(realne[2029])} mil.** Aby služby udržely úroveň roku 2025, potřebovaly by "
                    f"v roce 2029 **{kc(udrzeni[2029])} mil. Kč**."
                ),
                kind="info",
            ),
        ]
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.accordion(
        {
            "Zdroje a metodika": mo.md(
                """
                - **Program 2027–2029:** Návrh zákona o SR 2027, H_01 Struktura výdajů podle programového
                  financování, s. 7 (Z3531, kap. 335 MZd: 415 / 415 / 415 mil. Kč).
                - **Program 2024–2026:** Výroční zprávy RVKPZ 2024 a 2025, kap. 7, tab. 7-1 a 7-2;
                  zákon č. 38/2026 Sb.; seznam schválených dotací MZd 2026. Revidovaný vládní návrh SR 2026
                  počítal s 315 mil. Kč, +100 mil. doplnila Poslanecká sněmovna (březen 2026).
                - **Inflace a mzdy:** MF ČR, Makroekonomický rámec (D_01 k návrhu SR 2027) a Střednědobý
                  výhled 2028–2029 (K_01). Růst průměrné mzdy 2025, 2028 a 2029 je odvozený
                  (objem mezd a platů minus zaměstnanost).
                - **Příjmy z návykových produktů 2027:** Zpráva k návrhu SR 2027 (E_01) a SDV (K_01);
                  daň z hazardu jen podíl státního rozpočtu (bez 4,6 mld. pro obce).
                - **Rozdělení podle typu služby 2025:** VZ RVKPZ 2025, kap. 7, tab. 7-1 a 7-2 (dotace a požadavky,
                  součet obou výzev, zaokrouhleno na celé mil. Kč).
                - **Priority rozvoje 2027:** Výzva MZd k dotačnímu řízení Protidrogová politika na rok 2027, čl. 3,
                  dotační oblast I; oblasti a priority schválila vláda usnesením č. 609 ze dne 21. 9. 2026.
                  Alokace výzvy je podle čl. 4 „předmětem jednání“.
                - **Veřejné výdaje na služby 2024:** Souhrnná zpráva o závislostech v ČR 2025 (NMS), kap. 2.9.
                - **Dodatečná potřeba 600–800 mil. Kč:** odhad Jindřicha Vobořila (Zdravotnický deník,
                  30. 7. 2026), převzatý i ČTK (21. 9. 2026); metodika odhadu není zveřejněná.
                - **Výpočet:** reálná hodnota = nominální částka / index cen (nebo mezd) se základem 2025.
                  Odchylka od predikce se přičítá ke každému roku 2026–2029.
                """
            )
        }
    )
    return


if __name__ == "__main__":
    app.run()
