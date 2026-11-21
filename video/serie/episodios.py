# -*- coding: utf-8 -*-
"""Serie "Leonida" — ficcion de fans en 8 episodios de 30 segundos.

Continua la historia de Lucia y Jason despues del golpe que salio mal, con los
personajes que Rockstar presento en 2025. Todo lo que ocurre aqui es INVENTADO:
no es la trama del juego.

Cada episodio es una lista de planos (shots). Cada plano tiene un visual y las
frases de narracion que suenan mientras se ve. Los planos "card_*" son las
presentaciones de personaje.
"""

PERSONAJES = {
    "brian": dict(name="BRIAN HEDER", role="Contrabandista veterano de los Keys", color="#ffb15c",
                  fig=dict(hat="bucket", hair="short", beard=True, shirt="hawaii", build=1.25)),
    "cal": dict(name="CAL HAMPTON", role="Amigo de Jason · vive pegado a la radio", color="#22d3c5",
                fig=dict(hat="cap", hair="short", beard=True, glasses=True, shirt="tee", headset=True, build=1.05)),
    "boobie": dict(name="BOOBIE IKE", role="Leyenda de Vice City · club, música y edificios", color="#ffd166",
                   fig=dict(hair="bald", beard=True, sunglasses=True, shirt="suit", chain=True, build=1.2)),
    "drequan": dict(name="DRE'QUAN PRIEST", role="Mánager de Only Raw Records", color="#a26bff",
                    fig=dict(hat="cap_back", hair="short", shirt="hoodie", headphones=True, chain=True, build=1.0)),
    "dimez": dict(name="REAL DIMEZ", role="Bae-Luxe y Roxy · el dúo del momento", color="#ff3d8b",
                  duo=[dict(hair="long", shirt="top", mic=True, build=0.9), dict(hair="bun", shirt="top", sunglasses=True, build=0.9)]),
    "raul": dict(name="RAUL BAUTISTA", role="Ladrón de bancos veterano", color="#ff4d4d",
                 fig=dict(hair="slick", beard=True, shirt="suit", tie=True, build=1.05)),
}

EPISODIOS = [
    dict(num=1, title="Después del golpe", seed=1, shots=[
        dict(visual="highway", label="Leonida", lines=[
            "El golpe tenía que ser fácil. No lo fue.",
            "Con una bolsa ajena y media Leonida buscándolos, Lucía y Jason huyen hacia el sur, a los Keys.",
        ]),
        dict(visual="card_brian", char="brian", lines=[
            "Allí los espera el único hombre que no hace preguntas: Brian Heder, contrabandista de toda la vida y casero de Jason.",
        ]),
        dict(visual="keys_night", label="Leonida Keys", lines=[
            "«Pueden quedarse», dice Brian, «mientras alguien pague la renta».",
            "Lucía mira el mar. Por primera vez en días, pueden respirar.",
        ]),
    ]),
    dict(num=2, title="Ojos en el mar", seed=2, shots=[
        dict(visual="card_cal", char="cal", lines=[
            "Esa noche aparece Cal Hampton, el amigo más paranoico de Jason, con una cerveza en la mano y malas noticias.",
        ]),
        dict(visual="keys_night", radio=True, lines=[
            "Vive pegado a la radio de la guardia costera, y hoy no trae teorías.",
            "«Buscan a una pareja», dice. «Y no es la policía».",
        ]),
        dict(visual="disco", lines=[
            "Lucía abre la bolsa. No hay dinero: hay un disco duro con nombres, cuentas y fechas.",
            "Alguien muy poderoso quiere recuperarlo.",
        ]),
    ]),
    dict(num=3, title="El rey de Vice City", seed=3, shots=[
        dict(visual="neon_city", label="Vice City", lines=[
            "Para vender algo así hace falta un nombre grande, y en Vice City nadie es más grande que Boobie Ike.",
        ]),
        dict(visual="card_boobie", char="boobie", lines=[
            "Club nocturno, discográfica, edificios enteros. Si algo se mueve en Vice City, Boobie lo sabe.",
        ]),
        dict(visual="club", lines=[
            "Boobie mira el disco duro y deja de sonreír. «Esto no se vende», advierte. «Esto se usa».",
            "Y les ofrece un trato: protección, a cambio de una parte de lo que el disco esconda.",
        ]),
    ]),
    dict(num=4, title="Only Raw", seed=4, shots=[
        dict(visual="studio", lines=[
            "Boobie los esconde en su estudio, Only Raw Records, donde nadie hace preguntas si la música suena bien.",
        ]),
        dict(visual="card_drequan", char="drequan", lines=[
            "Allí manda Dre'Quan Priest, un mánager que sueña con su primer gran éxito.",
        ]),
        dict(visual="card_dimez", char="dimez", lines=[
            "Y lo tiene delante: Real Dimez, el dúo de Bae-Luxe y Roxy, que esa noche graba un video en el club.",
        ]),
        dict(visual="club", rec=True, lines=[
            "Nadie se da cuenta de que, al fondo de la toma, entre luces y humo, aparece Lucía. Y la cámara no perdona.",
        ]),
    ]),
    dict(num=5, title="Viral", seed=5, shots=[
        dict(visual="phones", viral=True, lines=[
            "A la mañana siguiente, el video tiene dos millones de vistas. Y alguien lo ha pausado en el segundo catorce.",
            "Dre'Quan intenta borrarlo, pero internet no olvida.",
        ]),
        dict(visual="street", label="Only Raw Records", lines=[
            "A mediodía, dos camionetas negras se detienen frente al estudio.",
        ]),
        dict(visual="highway", lines=[
            "Jason arranca el auto. Lucía no mira atrás. En Vice City, hacerse viral puede salir muy caro.",
        ]),
    ]),
    dict(num=6, title="El profesional", seed=6, shots=[
        dict(visual="port", label="Port Gellhorn", lines=[
            "Sin salida, Boobie hace una llamada a un viejo conocido.",
        ]),
        dict(visual="card_raul", char="raul", lines=[
            "Así llega Raul Bautista, ladrón de bancos veterano, elegante y paciente.",
        ]),
        dict(visual="disco", target=True, lines=[
            "Revisa el disco en silencio y encuentra lo que nadie vio: una bóveda privada en Port Gellhorn.",
        ]),
        dict(visual="duo", lines=[
            "«Un golpe más», dice Raul, «y serán libres para siempre». Lucía ya ha oído eso antes.",
        ]),
    ]),
    dict(num=7, title="El equipo", seed=7, shots=[
        dict(visual="team", lines=[
            "El plan toma forma en el viejo estudio. Raul dirige. Cal vigila la radio. Brian pone el barco. Boobie mueve el dinero.",
            "Y Real Dimez dará un concierto en directo en el puerto, para que todas las cámaras miren hacia otro lado.",
        ]),
        dict(visual="duo", lines=[
            "Esa noche, en el muelle, Jason toma la mano de Lucía. «Esta vez», promete, «nada sale mal». Ella quiere creerle.",
        ]),
    ]),
    dict(num=8, title="Noche en Port Gellhorn", seed=8, final=True, shots=[
        dict(visual="port_night", label="Port Gellhorn · 00:00", lines=[
            "Medianoche. El concierto empieza, las cámaras giran y el equipo entra.",
        ]),
        dict(visual="vault", lines=[
            "Todo va según el plan. Las cerraduras ceden una a una, hasta que la bóveda se abre. No hay dinero.",
        ]),
        dict(visual="vault", photo=True, lines=[
            "Solo una mesa vacía y una foto: Lucía y Jason, tomada esa misma mañana.",
        ]),
        dict(visual="black", lines=[
            "Las luces se apagan. Se oyen pasos. Alguien los estaba esperando.",
        ]),
    ]),
]

PRONUNCIACION_EXTRA = [
    ("Brian Heder", "Bráian Jéder"),
    ("Brian", "Bráian"),
    ("Cal Hampton", "Cal Jámpton"),
    ("Boobie Ike", "Búbi Áik"),
    ("Boobie", "Búbi"),
    ("Dre'Quan Priest", "Dre Kuán Prist"),
    ("Dre'Quan", "Dre Kuán"),
    ("Real Dimez", "Ríal Dáims"),
    ("Bae-Luxe", "Bei Lux"),
    ("Roxy", "Róxi"),
    ("Raul", "Raúl"),
    ("Only Raw Records", "Ónli Ro Récords"),
]
