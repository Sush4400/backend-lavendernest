"""
Management command to seed LavenderNest demo products into the database.

Usage:
    python manage.py seed_products --settings=lavendernest.settings.development
    python manage.py seed_products --clear  # wipe existing seed data first
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.products.models import Category, Product


CATEGORIES = [
    {
        "name": "Scented Candles",
        "slug": "candles",
        "description": "Hand-poured soy wax candles in beautiful, reusable jars — each one scented to calm, energise or simply delight.",
    },
    {
        "name": "Forever Flowers",
        "slug": "pipe-cleaner-flowers",
        "description": "Everlasting pipe-cleaner bouquets handcrafted to look freshly picked — no water needed, no petals ever fall.",
    },
    {
        "name": "Light Bottles",
        "slug": "light-bottles",
        "description": "Repurposed glass bottles strung with warm fairy lights — a little magic for any shelf or windowsill.",
    },
]

PRODUCTS = [
    # ── Candles ─────────────────────────────────────────────────────────────
    {
        "name": "Lavender Dreams Candle",
        "sku": "CNDL-001",
        "category_slug": "candles",
        "price": "349.00",
        "compare_at_price": "429.00",
        "stock": 45,
        "status": "active",
        "is_featured": True,
        "short_description": "A calming lavender and chamomile blend hand-poured into a frosted glass jar.",
        "description": (
            "Unwind with our bestselling Lavender Dreams. Each candle is hand-poured using "
            "100 % natural soy wax, a cotton wick, and a blend of French lavender and chamomile "
            "essential oils. The frosted glass jar doubles as a beautiful storage pot once the "
            "candle is done. Burn time approx. 40 hours."
        ),
        "care_instructions": "Trim wick to 5 mm before each use. Never burn more than 4 hours at a time.",
        "shipping_info": "Wrapped in recycled tissue and dispatched within 2 business days.",
        "tags": "lavender,soy,chamomile,relaxing,gift",
        "weight": "280",
        "subcategory": "glass",
        "details": {
            "Wax type": "100% natural soy wax",
            "Wick": "Unbleached cotton",
            "Fragrance": "French lavender & chamomile",
            "Burn time": "~40 hours",
            "Jar": "Frosted borosilicate glass",
            "Net weight": "200 g",
        },
    },
    {
        "name": "Rose Garden Candle",
        "sku": "CNDL-002",
        "category_slug": "candles",
        "price": "379.00",
        "compare_at_price": None,
        "stock": 30,
        "status": "active",
        "is_featured": True,
        "short_description": "Romantic rose and sandalwood — a warm, floral scent for quiet evenings.",
        "description": (
            "Inspired by a garden in full bloom, Rose Garden blends Bulgarian rose absolute "
            "with a soft sandalwood base. Hand-poured in small batches into an amber glass jar "
            "with a hand-tied ribbon. Makes a beautiful gift. Burn time approx. 35 hours."
        ),
        "care_instructions": "Keep away from drafts. Allow wax to melt fully across the surface on first burn.",
        "shipping_info": "Gift-wrapped and dispatched within 2 business days.",
        "tags": "rose,sandalwood,romantic,floral,gift",
        "weight": "260",
        "subcategory": "glass",
        "details": {
            "Wax type": "Soy & coconut wax blend",
            "Fragrance": "Bulgarian rose & sandalwood",
            "Burn time": "~35 hours",
            "Jar": "Amber glass",
            "Net weight": "190 g",
        },
    },
    {
        "name": "Vanilla Sky Soy Candle",
        "sku": "CNDL-003",
        "category_slug": "candles",
        "price": "299.00",
        "compare_at_price": "349.00",
        "stock": 60,
        "status": "active",
        "is_featured": False,
        "short_description": "Sweet vanilla and warm amber — comforting, cosy and utterly inviting.",
        "description": (
            "Vanilla Sky is the candle you light on lazy Sunday mornings. Madagascar vanilla "
            "and golden amber come together in a creamy soy wax base. Packaged in a clear "
            "glass tumbler with a reusable cork lid. Burn time approx. 30 hours."
        ),
        "care_instructions": "Store in a cool, dark place. Do not leave burning unattended.",
        "shipping_info": "Dispatched in 2–3 business days. Cork lid protects the candle during transit.",
        "tags": "vanilla,amber,cosy,sweet,everyday",
        "weight": "240",
        "subcategory": "glass",
        "details": {
            "Wax type": "100% soy wax",
            "Fragrance": "Madagascar vanilla & amber",
            "Burn time": "~30 hours",
            "Jar": "Clear glass tumbler with cork lid",
            "Net weight": "170 g",
        },
    },
    {
        "name": "Ocean Breeze Mini Candle Set",
        "sku": "CNDL-004",
        "category_slug": "candles",
        "price": "449.00",
        "compare_at_price": "549.00",
        "stock": 25,
        "status": "active",
        "is_featured": False,
        "short_description": "A set of three mini soy candles inspired by the sea — fresh, uplifting and gift-ready.",
        "description": (
            "The Ocean Breeze set contains three 60 g mini candles: Sea Salt & Driftwood, "
            "Coastal Eucalyptus, and Rain-washed Stone. Presented in a kraft box tied with "
            "jute twine — ready to gift or to create a little spa moment at home. "
            "Burn time approx. 15 hours each."
        ),
        "care_instructions": "Mini candles are best burned for no more than 2 hours at a time.",
        "shipping_info": "Ships in a sturdy kraft gift box within 2 business days.",
        "tags": "mini,set,ocean,sea,gift,eucalyptus",
        "weight": "220",
        "subcategory": "mini",
        "details": {
            "Contents": "3 × 60 g mini candles",
            "Scents": "Sea Salt & Driftwood, Coastal Eucalyptus, Rain-washed Stone",
            "Burn time": "~15 hours each",
            "Packaging": "Kraft gift box + jute twine",
        },
    },
    {
        "name": "Midnight Jasmine Candle",
        "sku": "CNDL-005",
        "category_slug": "candles",
        "price": "399.00",
        "compare_at_price": None,
        "stock": 18,
        "status": "active",
        "is_featured": False,
        "short_description": "Heady jasmine and warm musk for evenings that deserve a little drama.",
        "description": (
            "Midnight Jasmine is rich, intoxicating and utterly romantic. Night-blooming "
            "jasmine absolute is layered with soft white musk and a hint of black tea. "
            "Poured into a matte-black ceramic vessel that looks as gorgeous unlit as it does glowing. "
            "Burn time approx. 45 hours."
        ),
        "care_instructions": "The ceramic vessel retains heat — place on a heat-safe surface.",
        "shipping_info": "Padded and dispatched within 2–3 business days.",
        "tags": "jasmine,musk,black tea,evening,romantic,artistic",
        "weight": "320",
        "subcategory": "artistic",
        "details": {
            "Fragrance": "Jasmine absolute, white musk, black tea",
            "Vessel": "Matte-black ceramic",
            "Burn time": "~45 hours",
            "Net weight": "220 g",
        },
    },

    # ── Forever Flowers ──────────────────────────────────────────────────────
    {
        "name": "Blush Rose Bouquet",
        "sku": "FLWR-001",
        "category_slug": "pipe-cleaner-flowers",
        "price": "549.00",
        "compare_at_price": "649.00",
        "stock": 20,
        "status": "active",
        "is_featured": True,
        "short_description": "12 blush-pink pipe-cleaner roses — perfect as a forever keepsake or a thoughtful gift.",
        "description": (
            "Hand-twisted petal by petal, each rose in this bouquet takes about 20 minutes "
            "to make. Twelve flowers in shades of blush and ivory, tied with satin ribbon. "
            "These blooms will never wilt — a forever gift for someone forever special."
        ),
        "care_instructions": "Dust gently with a dry cloth. Keep away from direct sunlight to preserve colour.",
        "shipping_info": "Each bouquet is boxed in a gift-ready flower box within 2–3 business days.",
        "tags": "rose,blush,bouquet,forever,gift,handmade,flower",
        "weight": "120",
        "subcategory": "flower",
        "details": {
            "Stems": "12",
            "Colours": "Blush pink & ivory",
            "Material": "Aluminium pipe cleaners",
            "Ribbon": "Satin, dusty rose",
            "Height": "~30 cm",
        },
    },
    {
        "name": "Sunflower Sunshine Bunch",
        "sku": "FLWR-002",
        "category_slug": "pipe-cleaner-flowers",
        "price": "499.00",
        "compare_at_price": None,
        "stock": 15,
        "status": "active",
        "is_featured": False,
        "short_description": "Six cheerful yellow sunflowers with green stems — guaranteed to make anyone smile.",
        "description": (
            "Six hand-made sunflowers, each with individually twisted golden petals and a "
            "fuzzy brown centre. Wrapped in kraft paper with a handwritten tag. "
            "Brighten up any corner of your home — or someone else's."
        ),
        "care_instructions": "No water needed! Simply display and enjoy.",
        "shipping_info": "Wrapped carefully and dispatched within 2 business days.",
        "tags": "sunflower,yellow,bright,happy,gift,flower",
        "weight": "90",
        "subcategory": "flower",
        "details": {
            "Stems": "6",
            "Colours": "Golden yellow with brown centres",
            "Material": "Aluminium pipe cleaners",
            "Height": "~35 cm",
        },
    },
    {
        "name": "Wildflower Meadow Arrangement",
        "sku": "FLWR-003",
        "category_slug": "pipe-cleaner-flowers",
        "price": "699.00",
        "compare_at_price": "849.00",
        "stock": 10,
        "status": "active",
        "is_featured": True,
        "short_description": "A lush mixed-wildflower arrangement in a hand-painted ceramic pot.",
        "description": (
            "Lavender, daisies, poppies and baby's breath — all handcrafted and arranged "
            "in a hand-painted ceramic pot. Each arrangement is one-of-a-kind. "
            "Measuring approx. 25 cm tall, it sits beautifully on a desk, shelf or windowsill."
        ),
        "care_instructions": "Wipe petals with a slightly damp cloth if dusty. Do not submerge.",
        "shipping_info": "The ceramic pot is bubble-wrapped before dispatch. Allow 3–4 business days.",
        "tags": "wildflower,arrangement,lavender,daisy,poppy,ceramic,gift,artistic",
        "weight": "350",
        "subcategory": "artistic",
        "details": {
            "Flowers": "Lavender, daisy, poppy, baby's breath",
            "Pot": "Hand-painted ceramic, 8 cm",
            "Height": "~25 cm",
            "Material": "Aluminium pipe cleaners",
        },
    },
    {
        "name": "Pastel Rainbow Mini Bouquet",
        "sku": "FLWR-004",
        "category_slug": "pipe-cleaner-flowers",
        "price": "399.00",
        "compare_at_price": None,
        "stock": 35,
        "status": "active",
        "is_featured": False,
        "short_description": "Seven pastel blooms — one for every colour of the rainbow.",
        "description": (
            "Seven flowers in soft pastel shades — lavender, mint, peach, lemon, baby blue, "
            "lilac and rose. Each stem is wrapped in matching ribbon. A sweet gift for birthdays, "
            "anniversaries or 'just because' days. Approx. 28 cm tall."
        ),
        "care_instructions": "Keep out of prolonged direct sunlight to maintain pastel tones.",
        "shipping_info": "Dispatched in a protective flower box within 2 business days.",
        "tags": "pastel,rainbow,mini,birthday,gift,colourful,flower",
        "weight": "85",
        "subcategory": "mini",
        "details": {
            "Stems": "7",
            "Colours": "7 pastel shades",
            "Height": "~28 cm",
            "Occasion": "Birthday, anniversary, gift",
        },
    },

    # ── Light Bottles ────────────────────────────────────────────────────────
    {
        "name": "Vintage Amber Fairy-Light Bottle",
        "sku": "LTBT-001",
        "category_slug": "light-bottles",
        "price": "449.00",
        "compare_at_price": "529.00",
        "stock": 22,
        "status": "active",
        "is_featured": True,
        "short_description": "A repurposed amber bottle filled with warm-white fairy lights — magical on any shelf.",
        "description": (
            "We upcycle vintage-style amber bottles and fill them with a string of 30 warm-white "
            "LED fairy lights. USB-powered with a toggle switch. Glows beautifully in a dim room "
            "and makes a lovely nightlight or centrepiece. Height approx. 22 cm."
        ),
        "care_instructions": "USB-powered only. Do not expose to water. Handle with care — glass.",
        "shipping_info": "Bubble-wrapped and boxed. Dispatched within 2–3 business days.",
        "tags": "fairy lights,bottle,amber,USB,nightlight,vintage,decor",
        "weight": "280",
        "subcategory": "glass",
        "details": {
            "Bottle": "Amber glass, upcycled",
            "Lights": "30 warm-white LED",
            "Power": "USB (cable included)",
            "Switch": "Toggle switch on cable",
            "Height": "~22 cm",
        },
    },
    {
        "name": "Clear Glass Star-Light Bottle",
        "sku": "LTBT-002",
        "category_slug": "light-bottles",
        "price": "399.00",
        "compare_at_price": None,
        "stock": 28,
        "status": "active",
        "is_featured": False,
        "short_description": "Star-shaped LED lights inside a tall clear glass bottle — dreamy and delicate.",
        "description": (
            "Forty tiny star-shaped warm LEDs nestled inside a slender clear glass bottle. "
            "Battery-powered (3 × AA, not included) with an auto-off timer. "
            "Lovely on a bedside table or as part of a shelfie."
        ),
        "care_instructions": "Replace batteries when lights dim. Do not leave on unattended for extended periods.",
        "shipping_info": "Safely packaged in bubble wrap. Dispatched within 2 business days.",
        "tags": "star,fairy lights,clear,battery,dreamy,bedside,decor",
        "weight": "220",
        "subcategory": "glass",
        "details": {
            "Bottle": "Clear borosilicate glass",
            "Lights": "40 star-shaped warm LEDs",
            "Power": "3 × AA battery (not included)",
            "Timer": "6 hrs on / 18 hrs off",
            "Height": "~28 cm",
        },
    },
    {
        "name": "Frosted Globe Petal-Light Bottle",
        "sku": "LTBT-003",
        "category_slug": "light-bottles",
        "price": "529.00",
        "compare_at_price": "629.00",
        "stock": 12,
        "status": "active",
        "is_featured": False,
        "short_description": "Dried flower petals and warm copper-wire lights in a frosted globe bottle.",
        "description": (
            "A frosted spherical glass bottle filled with dried lavender petals and a copper-wire "
            "LED string. The petals glow softly when lit. Battery-powered with a convenient switch. "
            "A truly one-of-a-kind decorative piece. Diameter approx. 12 cm."
        ),
        "care_instructions": "Do not shake. Handle gently — the dried petals are delicate.",
        "shipping_info": "Extra-padded for safety. Please allow 3–4 business days.",
        "tags": "petal,lavender,frosted,copper,globe,decorative,unique",
        "weight": "310",
        "subcategory": "artistic",
        "details": {
            "Bottle": "Frosted glass globe, ~12 cm diameter",
            "Fill": "Dried lavender petals",
            "Lights": "Copper-wire warm LED",
            "Power": "2 × AA battery (not included)",
        },
    },
    {
        "name": "Recycled Bottle Cluster Set",
        "sku": "LTBT-004",
        "category_slug": "light-bottles",
        "price": "799.00",
        "compare_at_price": "949.00",
        "stock": 8,
        "status": "active",
        "is_featured": False,
        "short_description": "Three mismatched recycled bottles connected by a single fairy-light strand — art for your shelf.",
        "description": (
            "Three uniquely shaped recycled bottles — green, amber and clear — connected by a single "
            "50-LED warm-white strand. One USB plug powers all three. Each set is assembled by hand "
            "so no two are identical. Sold as a complete set. Recommended surface: 40 cm wide."
        ),
        "care_instructions": "USB-powered only. Not suitable for outdoor use.",
        "shipping_info": "Carefully assembled and boxed. Please allow 3–5 business days.",
        "tags": "cluster,set,recycled,green,amber,USB,shelf,decor",
        "weight": "680",
        "subcategory": "seasonal",
        "details": {
            "Bottles": "3 × mismatched recycled glass",
            "Lights": "50 warm-white LED",
            "Power": "USB (cable included)",
            "Width": "~40 cm assembled",
        },
    },
]


class Command(BaseCommand):
    help = "Seed the database with LavenderNest demo products and categories."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing seed products and categories before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["clear"]:
            skus = [p["sku"] for p in PRODUCTS]
            deleted, _ = Product.objects.filter(sku__in=skus).delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} existing seed product(s)."))
            slugs = [c["slug"] for c in CATEGORIES]
            deleted, _ = Category.objects.filter(slug__in=slugs).delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} existing seed category(ies)."))

        # Create / update categories
        category_map = {}
        for cat_data in CATEGORIES:
            cat, created = Category.objects.update_or_create(
                slug=cat_data["slug"],
                defaults={
                    "name": cat_data["name"],
                    "description": cat_data["description"],
                    "is_active": True,
                },
            )
            category_map[cat_data["slug"]] = cat
            verb = "Created" if created else "Updated"
            self.stdout.write(f"  {verb} category: {cat.name}")

        # Create / update products
        created_count = 0
        updated_count = 0
        for prod_data in PRODUCTS:
            category = category_map.get(prod_data.pop("category_slug"))
            prod_data["category"] = category
            prod_data["details"] = prod_data.get("details", {})

            _, created = Product.objects.update_or_create(
                sku=prod_data["sku"],
                defaults=prod_data,
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSeeding complete: {created_count} product(s) created, "
                f"{updated_count} product(s) updated."
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "  Run 'python manage.py createsuperuser' to create an admin account."
            )
        )
