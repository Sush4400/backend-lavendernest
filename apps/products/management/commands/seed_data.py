import os
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.products.models import Category, Product, ProductImage
from apps.users.models import Customer, Address

User = get_user_model()

class Command(BaseCommand):
    help = "Seed database with handcrafted products, categories, and test user"

    def handle(self, *args, **options):
        self.stdout.write("Seeding LavenderNest database...")

        # 1. Superuser / Test User
        admin_user, created = User.objects.get_or_create(
            email="admin@lavendernest.com",
            defaults={
                "first_name": "Eleanor",
                "last_name": "Vane",
                "role": User.Role.ADMIN,
                "is_staff": True,
                "is_superuser": True,
            }
        )
        if created:
            admin_user.set_password("admin12345")
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("Created admin: admin@lavendernest.com / admin12345"))

        # Test customer user
        test_user, created = User.objects.get_or_create(
            email="customer@lavendernest.com",
            defaults={
                "first_name": "Sophia",
                "last_name": "Rose",
                "role": User.Role.CUSTOMER,
            }
        )
        if created:
            test_user.set_password("customer12345")
            test_user.save()
            customer_profile, _ = Customer.objects.get_or_create(
                user=test_user,
                defaults={"phone_number": "+1 555-019-2834"}
            )
            Address.objects.get_or_create(
                customer=customer_profile,
                defaults={
                    "full_name": "Sophia Rose",
                    "phone_number": "+1 555-019-2834",
                    "address_line1": "742 Evergreen Terrace",
                    "city": "Springfield",
                    "state": "Oregon",
                    "postal_code": "97477",
                    "country": "United States",
                    "is_default": True,
                }
            )
            self.stdout.write(self.style.SUCCESS("Created customer: customer@lavendernest.com / customer12345"))

        # 2. Categories
        categories_data = [
            {
                "name": "Handcrafted Candles",
                "slug": "handcrafted-candles",
                "description": "Slow-burning soy and beeswax candles infused with organic botanical oils, soothing lavender, and dried florals.",
            },
            {
                "name": "Pipe Cleaner Flowers",
                "slug": "pipe-cleaner-flowers",
                "description": "Forever-blooming handcrafted floral bouquets sculpted with premium plush chenille stems and artistic flair.",
            },
            {
                "name": "Artisanal Home Decor",
                "slug": "home-decor",
                "description": "Earthy pottery, rustic woven accents, and serene interior details that bring botanical calm into your home.",
            },
            {
                "name": "Luxury Gift Sets",
                "slug": "gift-sets",
                "description": "Carefully wrapped gift bundles combining aromatic candles, timeless forever blooms, and bespoke keepsakes.",
            },
        ]

        cat_objs = {}
        for cdata in categories_data:
            cat, _ = Category.objects.update_or_create(
                slug=cdata["slug"],
                defaults={
                    "name": cdata["name"],
                    "description": cdata["description"],
                    "is_active": True,
                }
            )
            cat_objs[cat.slug] = cat

        # 3. Products
        products_data = [
            {
                "category": cat_objs["handcrafted-candles"],
                "name": "Provencal Lavender & Wild Honey Soy Candle",
                "slug": "provencal-lavender-wild-honey-soy-candle",
                "description": "Hand-poured with 100% natural soy wax, authentic French lavender essential oil, and notes of warm wild honey. Hand-topped with harvested dried lavender sprigs. Burns cleanly for up to 55 hours.",
                "short_description": "100% soy candle with natural French lavender & sweet honey notes.",
                "sku": "LAV-CNDL-001",
                "price": Decimal("28.00"),
                "compare_at_price": Decimal("35.00"),
                "stock": 24,
                "weight": Decimal("380.00"),
                "status": Product.Status.ACTIVE,
                "is_featured": True,
                "tags": "candle,lavender,soy wax,aromatherapy,organic",
                "image_url": "https://images.unsplash.com/photo-1603006905003-be475563bc59?auto=format&fit=crop&w=800&q=80",
            },
            {
                "category": cat_objs["handcrafted-candles"],
                "name": "Midnight Amber & Smoked Cedarwood Candle",
                "slug": "midnight-amber-smoked-cedarwood-candle",
                "description": "A grounding evening fragrance made with coconut-apricot wax, crackling wooden wicks, and deep notes of golden amber, cedarwood, and delicate vanilla smoke.",
                "short_description": "Wooden wick candle with smoky cedar and warm golden amber.",
                "sku": "LAV-CNDL-002",
                "price": Decimal("32.00"),
                "compare_at_price": Decimal("40.00"),
                "stock": 18,
                "weight": Decimal("400.00"),
                "status": Product.Status.ACTIVE,
                "is_featured": True,
                "tags": "candle,amber,cedarwood,wooden wick,luxury",
                "image_url": "https://images.unsplash.com/photo-1572726729207-a78d6feb18d7?auto=format&fit=crop&w=800&q=80",
            },
            {
                "category": cat_objs["handcrafted-candles"],
                "name": "Frosted Vanilla & Chamomile Tea Candle",
                "slug": "frosted-vanilla-chamomile-tea-candle",
                "description": "Subtle, relaxing aromas of whipped Bourbon vanilla bean and dried chamomile blossoms. Housed in a matte ceramic reusable vessel.",
                "short_description": "Bourbon vanilla and calming chamomile in a reusable matte ceramic jar.",
                "sku": "LAV-CNDL-003",
                "price": Decimal("26.00"),
                "compare_at_price": None,
                "stock": 15,
                "weight": Decimal("350.00"),
                "status": Product.Status.ACTIVE,
                "is_featured": False,
                "tags": "candle,vanilla,chamomile,relax,ceramic",
                "image_url": "https://images.unsplash.com/photo-1543257580-7269da773bf5?auto=format&fit=crop&w=800&q=80",
            },
            {
                "category": cat_objs["pipe-cleaner-flowers"],
                "name": "Eternal Lavender & Tulip Chenille Bouquet",
                "slug": "eternal-lavender-tulip-chenille-bouquet",
                "description": "A delicate, handcrafted forever bouquet meticulously shaped from ultra-soft pipe cleaners and wrapped in textured craft paper with satin ribbon. Features 5 lavender stalks, 3 pastel pink tulips, and eucalyptus greens.",
                "short_description": "Never-wilting handcrafted bouquet of plush lavender stalks and pastel tulips.",
                "sku": "LAV-FLWR-001",
                "price": Decimal("44.00"),
                "compare_at_price": Decimal("52.00"),
                "stock": 12,
                "weight": Decimal("200.00"),
                "status": Product.Status.ACTIVE,
                "is_featured": True,
                "tags": "flowers,pipe cleaner,forever flowers,bouquet,handcrafted",
                "image_url": "https://images.unsplash.com/photo-1563245372-f21724e3856d?auto=format&fit=crop&w=800&q=80",
            },
            {
                "category": cat_objs["pipe-cleaner-flowers"],
                "name": "Sunny Meadow Chenille Daisy & Sunflower Bunch",
                "slug": "sunny-meadow-chenille-daisy-sunflower-bunch",
                "description": "Brimming with cheerful golden sunflowers and miniature white daisies. Handmade with wire-core chenille stems that can be gently shaped and posed to fit any vase.",
                "short_description": "Cheerful golden sunflowers and daisies sculpted with velvety chenille.",
                "sku": "LAV-FLWR-002",
                "price": Decimal("38.00"),
                "compare_at_price": None,
                "stock": 20,
                "weight": Decimal("180.00"),
                "status": Product.Status.ACTIVE,
                "is_featured": True,
                "tags": "sunflower,daisy,chenille,flowers,bright",
                "image_url": "https://images.unsplash.com/photo-1508610048659-a06b669e3321?auto=format&fit=crop&w=800&q=80",
            },
            {
                "category": cat_objs["pipe-cleaner-flowers"],
                "name": "Lilac Dream Velvet Hydrangea Stem Set",
                "slug": "lilac-dream-velvet-hydrangea-stem-set",
                "description": "An intricate cluster of purple, lavender, and periwinkle petals fashioned one-by-one by hand. Includes 3 full stems with realistic green leaves.",
                "short_description": "Intricate cluster of pastel purple and lilac handcrafted petals.",
                "sku": "LAV-FLWR-003",
                "price": Decimal("36.00"),
                "compare_at_price": Decimal("42.00"),
                "stock": 9,
                "weight": Decimal("150.00"),
                "status": Product.Status.ACTIVE,
                "is_featured": False,
                "tags": "hydrangea,lilac,pipe cleaner,floral decor",
                "image_url": "https://images.unsplash.com/photo-1526047932273-341f2a7631f9?auto=format&fit=crop&w=800&q=80",
            },
            {
                "category": cat_objs["home-decor"],
                "name": "Artisanal Fluted Ceramic Vase - Lilac Haze",
                "slug": "artisanal-fluted-ceramic-vase-lilac-haze",
                "description": "Wheel-thrown by studio artisans and finished in a subtle, semi-matte lilac haze reactive glaze. Perfect for pairing with our chenille flower bouquets or dried floral stems.",
                "short_description": "Wheel-thrown ceramic vase with soft lilac glaze and fluted silhouette.",
                "sku": "LAV-DECR-001",
                "price": Decimal("48.00"),
                "compare_at_price": Decimal("58.00"),
                "stock": 14,
                "weight": Decimal("650.00"),
                "status": Product.Status.ACTIVE,
                "is_featured": True,
                "tags": "ceramic,vase,decor,artisan,pottery",
                "image_url": "https://images.unsplash.com/photo-1612196808214-b8e1d6145a8c?auto=format&fit=crop&w=800&q=80",
            },
            {
                "category": cat_objs["home-decor"],
                "name": "Natural Cotton Macrame Wall Hanging - Lavender Dreams",
                "slug": "natural-cotton-macrame-wall-hanging",
                "description": "Bohemian wall tapestry hand-knotted with 100% organic unbleached cotton rope dyed with botanical lavender extracts, suspended from a smooth reclaimed birch branch.",
                "short_description": "Hand-knotted organic cotton macrame with natural botanical lavender dye.",
                "sku": "LAV-DECR-002",
                "price": Decimal("54.00"),
                "compare_at_price": None,
                "stock": 7,
                "weight": Decimal("500.00"),
                "status": Product.Status.ACTIVE,
                "is_featured": False,
                "tags": "macrame,boho,wall hanging,cotton,tapestry",
                "image_url": "https://images.unsplash.com/photo-1582582621959-48d27397dc69?auto=format&fit=crop&w=800&q=80",
            },
            {
                "category": cat_objs["gift-sets"],
                "name": "The Serenity Ritual Luxury Gift Hamper",
                "slug": "the-serenity-ritual-luxury-gift-hamper",
                "description": "The ultimate luxury present. Includes the Provencal Lavender Soy Candle, a bespoke mini chenille bouquet, botanical bath salts, and a hand-dipped matches bottle, presented in our signature embossed wooden gift box.",
                "short_description": "All-in-one luxury relaxation gift box with candle, bouquet, and bath salts.",
                "sku": "LAV-GIFT-001",
                "price": Decimal("85.00"),
                "compare_at_price": Decimal("105.00"),
                "stock": 10,
                "weight": Decimal("1200.00"),
                "status": Product.Status.ACTIVE,
                "is_featured": True,
                "tags": "gift set,hamper,luxury,pamper,holiday,candles",
                "image_url": "https://images.unsplash.com/photo-1549465220-1a8b9238cd48?auto=format&fit=crop&w=800&q=80",
            },
            {
                "category": cat_objs["gift-sets"],
                "name": "Botanical Keepsake Blossom & Candle Duo",
                "slug": "botanical-keepsake-blossom-candle-duo",
                "description": "A heartfelt pairing of our customer-favorite Chamomile Candle and an everlasting miniature daisy bud, tied with pure mulberry silk ribbon and custom calligraphy greeting card.",
                "short_description": "Charming duo of artisan candle, keepsake bloom, and calligraphy card.",
                "sku": "LAV-GIFT-002",
                "price": Decimal("42.00"),
                "compare_at_price": Decimal("48.00"),
                "stock": 16,
                "weight": Decimal("450.00"),
                "status": Product.Status.ACTIVE,
                "is_featured": False,
                "tags": "gift duo,candle,flower,birthday,anniversary",
                "image_url": "https://images.unsplash.com/photo-1513519245088-0e12902e5a38?auto=format&fit=crop&w=800&q=80",
            },
        ]

        for pdata in products_data:
            image_url = pdata.pop("image_url", None)
            prod, _ = Product.objects.update_or_create(
                sku=pdata["sku"],
                defaults=pdata,
            )

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {len(products_data)} products across {len(categories_data)} categories!"))
