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
        # Kolik má adiktologie v rozpočtu doopravdy

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
            mo.md("## 1 · Stejná částka, menší hodnota"),
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
def _(mo):
    potreba = mo.ui.slider(
        start=0,
        stop=1000,
        step=50,
        value=700,
        show_value=True,
        label="**Dodatečná potřeba služeb** (mil. Kč ročně)",
    )
    mo.vstack(
        [
            mo.md(
                """
                ## 2 · Mezera mezi penězi a potřebou

                Žadatelé v dotačním řízení každý rok žádají víc, než program rozdělí, a to i přesto,
                že výzva sama omezuje, o kolik lze žádat (spolufinancování, stropy). Odborníci z oboru
                odhadují, že k plnému pokrytí služeb chybí **600–800 mil. Kč ročně** navíc.
                Posuvníkem si nastavíte vlastní předpoklad.
                """
            ),
            potreba,
        ]
    )
    return (potreba,)


@app.cell(hide_code=True)
def _(AMBER, CYAN, POZADAVKY, PROGRAM, SILVER, alt, kc, pd, potreba):
    _rows = [
        ("2024 · přiděleno", PROGRAM[2024], "přiděleno"),
        ("2024 · požadováno", POZADAVKY[2024], "požadováno"),
        ("2025 · přiděleno", PROGRAM[2025], "přiděleno"),
        ("2025 · požadováno", POZADAVKY[2025], "požadováno"),
        ("2027 · v návrhu SR", PROGRAM[2027], "přiděleno"),
        ("2027 · odhad potřeby", PROGRAM[2027] + potreba.value, "potřeba"),
    ]
    _df = pd.DataFrame(_rows, columns=["položka", "mil", "typ"])
    _df["popis"] = _df["mil"].map(lambda v: f"{kc(v, 1 if v % 1 else 0)} mil. Kč")
    _barvy = alt.Scale(domain=["přiděleno", "požadováno", "potřeba"], range=[CYAN, "#B9C4C4", AMBER])
    _base = alt.Chart(_df).encode(
        y=alt.Y("položka:N", sort=None, title=None, axis=alt.Axis(labelFontSize=13, labelLimit=220)),
        x=alt.X("mil:Q", title="mil. Kč", scale=alt.Scale(domain=[0, 1500]),
                axis=alt.Axis(grid=True, gridColor="#e6e6e6",
                              labelExpr="replace(format(datum.value, ','), ',', ' ')")),
    )
    graf_mezera = (
        (
            _base.mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4, height=26).encode(
                color=alt.Color("typ:N", scale=_barvy, title=None,
                                legend=alt.Legend(orient="top", labelFontSize=13, labelLimit=0)),
                tooltip=[alt.Tooltip("položka:N", title="Položka"), alt.Tooltip("popis:N", title="Částka")],
            )
            + _base.mark_text(align="left", dx=6, fontSize=12, color="#222").encode(text="popis:N")
        )
        .properties(height=280, width="container",
                    title=alt.Title("Přiděleno, požadováno, potřebné",
                                    subtitle="Požadavky žadatelů 2024 a 2025 podle výročních zpráv RVKPZ",
                                    anchor="start", fontSize=15, subtitleFontSize=12))
        .configure_view(strokeWidth=0)
        .configure_axis(domainColor="#999", labelColor="#333", titleColor="#555")
    )
    graf_mezera
    return


@app.cell(hide_code=True)
def _(POZADAVKY, PROGRAM, kc, mo, potreba):
    _nepokryto_24 = POZADAVKY[2024] - PROGRAM[2024]
    _nepokryto_25 = POZADAVKY[2025] - PROGRAM[2025]
    mo.md(
        f"""
        V roce 2024 zůstalo bez krytí **{kc(_nepokryto_24, 1)} mil. Kč** požadavků
        ({kc(_nepokryto_24 / POZADAVKY[2024] * 100)} %), v roce 2025 **{kc(_nepokryto_25, 1)} mil. Kč**
        ({kc(_nepokryto_25 / POZADAVKY[2025] * 100)} %).
        Při dodatečné potřebě {kc(potreba.value)} mil. Kč by program musel mít
        **{kc(PROGRAM[2027] + potreba.value)} mil. Kč**, tedy
        {kc((PROGRAM[2027] + potreba.value) / PROGRAM[2027], 1)}× víc než v návrhu.
        """
    )
    return


@app.cell(hide_code=True)
def _():
    # Priority a výchozí varianty – inspirace: GD „Podklady k debatě o rozpočtu na politiku
    # závislostí 2025“ (srpen 2024). Částky v mil. Kč. Neuvedené položky = 0.
    PRIORITY = {
        "sluzby": ("Adiktologické služby a kapacity",
                   "personál a dostupnost ve všech krajích, nové ambulance a centra"),
        "substituce": ("Substituční léčba",
                       "včetně nových programů pro lidi užívající pervitin"),
        "hr": ("Prevence a harm reduction",
               "injekční sety, testování infekcí, naloxon, osvěta pro rizikové skupiny"),
        "digital": ("Digitální závislosti a hazard",
                    "specializovaná centra a ambulantní péče"),
        "alkohol": ("Alkohol a tabák",
                    "ambulance v krajských městech, lidé s komorbiditami"),
        "zranitelni": ("Zranitelné skupiny",
                       "matky s dětmi, stárnoucí uživatelé, chráněné bydlení a zaměstnávání"),
        "valorizace": ("Valorizace mezd a nákladů",
                       "inflace, mzdy, energie"),
    }
    VARIANTY = {
        "Minimalistická": {"sluzby": 250, "substituce": 30, "hr": 60, "digital": 0,
                           "alkohol": 0, "zranitelni": 0, "valorizace": 69},
        "Kompromisní": {"sluzby": 200, "substituce": 40, "hr": 80, "digital": 40,
                        "alkohol": 0, "zranitelni": 0, "valorizace": 69},
        "Ideální": {"sluzby": 450, "substituce": 100, "hr": 250, "digital": 120,
                    "alkohol": 200, "zranitelni": 150, "valorizace": 100},
    }
    # Celkové částky, jak je uvádí podklad (součty položek se od nich liší)
    VARIANTY_UVEDENO = {"Minimalistická": 415, "Kompromisní": 500, "Ideální": 1100}
    return PRIORITY, VARIANTY, VARIANTY_UVEDENO


@app.cell(hide_code=True)
def _(VARIANTY, mo):
    varianta = mo.ui.dropdown(
        options=list(VARIANTY),
        value="Kompromisní",
        label="**Začít od varianty**",
    )
    mo.vstack(
        [
            mo.md(
                """
                ## 3 · Na co by peníze šly

                Vyberte výchozí variantu a posuvníky upravte jednotlivé priority.
                Kalkulačka sečte, kolik by takový program stál, a porovná to s návrhem rozpočtu.
                """
            ),
            varianta,
        ]
    )
    return (varianta,)


@app.cell(hide_code=True)
def _(PRIORITY, VARIANTY, mo, varianta):
    _v = VARIANTY[varianta.value]
    alokace = mo.ui.dictionary(
        {
            k: mo.ui.slider(start=0, stop=600, step=10, value=_v[k], show_value=True,
                            label=PRIORITY[k][0], full_width=True)
            for k in PRIORITY
        }
    )
    mo.vstack(
        [
            mo.vstack([alokace[k], mo.md(f"<small>{PRIORITY[k][1]}</small>")], gap=0)
            for k in PRIORITY
        ],
        gap=0.75,
    )
    return (alokace,)


@app.cell(hide_code=True)
def _(
    CYAN,
    PRIJMY_2027,
    PRIORITY,
    PROGRAM,
    PURPLE,
    VARIANTY,
    VARIANTY_UVEDENO,
    alokace,
    alt,
    kc,
    mo,
    pd,
    udrzeni,
    varianta,
):
    _hodnoty = alokace.value
    _celkem = sum(_hodnoty.values())
    _vychozi = VARIANTY[varianta.value]
    _prijmy = sum(PRIJMY_2027.values()) * 1000
    _vase = "Vaše rozdělení"
    _vych = f"Varianta {varianta.value.lower()}"
    _df = pd.DataFrame(
        [{"priorita": PRIORITY[k][0], "řada": _vase, "mil": _hodnoty[k],
          "popis": f"{kc(_hodnoty[k])} mil. Kč"} for k in PRIORITY]
        + [{"priorita": PRIORITY[k][0], "řada": _vych, "mil": _vychozi[k],
            "popis": f"{kc(_vychozi[k])} mil. Kč"} for k in PRIORITY]
    )
    _poradi = [PRIORITY[k][0] for k in PRIORITY]
    _barvy = alt.Scale(domain=[_vase, _vych], range=[CYAN, PURPLE])
    _base = alt.Chart(_df).encode(
        y=alt.Y("priorita:N", sort=_poradi, title=None,
                axis=alt.Axis(labelFontSize=13, labelLimit=260)),
        x=alt.X("mil:Q", title="mil. Kč", scale=alt.Scale(domain=[0, 600]),
                axis=alt.Axis(grid=True, gridColor="#e6e6e6")),
        color=alt.Color("řada:N", scale=_barvy, title=None,
                        legend=alt.Legend(orient="top", labelFontSize=13, labelLimit=0)),
        tooltip=[alt.Tooltip("priorita:N", title="Priorita"), alt.Tooltip("řada:N", title="Řada"),
                 alt.Tooltip("popis:N", title="Částka")],
    )
    _graf = (
        (
            _base.transform_filter(alt.datum["řada"] == _vase).mark_bar(
                cornerRadiusTopRight=4, cornerRadiusBottomRight=4, height=24)
            + _base.transform_filter(alt.datum["řada"] == _vych).mark_tick(
                thickness=3, size=34, opacity=1)
        )
        .properties(height=320, width="container",
                    title=alt.Title("Rozdělení podle priorit",
                                    subtitle="Sloupec = vaše nastavení, svislá čárka = výchozí varianta",
                                    anchor="start", fontSize=15, subtitleFontSize=12))
        .configure_view(strokeWidth=0)
        .configure_axis(domainColor="#999", labelColor="#333", titleColor="#555")
    )
    _rozdil = _celkem - PROGRAM[2027]
    _soucet_var = sum(_vychozi.values())
    mo.vstack(
        [
            _graf,
            mo.hstack(
                [
                    mo.stat(value=f"{kc(_celkem)} mil.", label="Program podle vašich priorit",
                            caption=f"{kc(_celkem / _prijmy * 100, 2)} % příjmů z návykových produktů",
                            bordered=True),
                    mo.stat(value=f"{'+' if _rozdil >= 0 else '−'}{kc(abs(_rozdil))} mil.",
                            label="Proti návrhu SR 2027 (415 mil.)",
                            caption=f"návrh pokryje {kc(min(PROGRAM[2027] / _celkem, 1) * 100 if _celkem else 100)} % vašeho rozdělení",
                            bordered=True),
                    mo.stat(value=f"{kc(udrzeni[2027])} mil.",
                            label="Jen udržení úrovně 2025 v roce 2027",
                            caption="podle přepočtu v části 1",
                            bordered=True),
                ],
                widths="equal", gap=1, wrap=True,
            ),
            mo.md(
                f"<small>Výchozí varianty vycházejí z podkladu k debatě o rozpočtu na politiku závislostí 2025 (srpen 2024). "
                f"Varianta {varianta.value.lower()} je v podkladu uvedena za {kc(VARIANTY_UVEDENO[varianta.value])} mil. Kč, "
                f"součet jejích položek je {kc(_soucet_var)} mil. Kč.</small>"
            ),
        ]
    )
    return


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
                ## 4 · Peníze, které stát z návykových produktů vybírá

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
            mo.md("## Věta ke sdílení"),
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
