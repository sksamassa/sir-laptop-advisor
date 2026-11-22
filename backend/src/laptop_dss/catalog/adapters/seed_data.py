"""Demo catalog used by the idempotent seed. Prices are in kopecks."""

from __future__ import annotations

DEMO_MODELS: list[dict[str, object]] = [
    {
        "brand": "Lenovo", "model_name": "IdeaPad 5 15", "slug": "lenovo-ideapad-5-15",
        "os": "windows", "form_factor": "laptop", "price_minor": 64_990_00,
        "cpu_score": 5_400, "ram_gb": 16, "weight_g": 1_700, "battery_minutes": 480,
        "screen_score": 6.5, "warranty_months": 12,
    },
    {
        "brand": "ASUS", "model_name": "ZenBook 14 OLED", "slug": "asus-zenbook-14-oled",
        "os": "windows", "form_factor": "ultrabook", "price_minor": 89_990_00,
        "cpu_score": 7_800, "ram_gb": 16, "weight_g": 1_250, "battery_minutes": 720,
        "screen_score": 9.2, "warranty_months": 24,
    },
    {
        "brand": "Apple", "model_name": "MacBook Air 13 M3", "slug": "apple-macbook-air-13-m3",
        "os": "macos", "form_factor": "ultrabook", "price_minor": 119_990_00,
        "cpu_score": 8_900, "ram_gb": 16, "weight_g": 1_240, "battery_minutes": 900,
        "screen_score": 9.0, "warranty_months": 12,
    },
    {
        "brand": "HP", "model_name": "Pavilion 15", "slug": "hp-pavilion-15",
        "os": "windows", "form_factor": "laptop", "price_minor": 54_990_00,
        "cpu_score": 4_200, "ram_gb": 8, "weight_g": 1_750, "battery_minutes": 360,
        "screen_score": 6.0, "warranty_months": 12,
    },
    {
        "brand": "Acer", "model_name": "Nitro 5", "slug": "acer-nitro-5",
        "os": "windows", "form_factor": "gaming", "price_minor": 94_990_00,
        "cpu_score": 8_200, "ram_gb": 16, "weight_g": 2_500, "battery_minutes": 240,
        "screen_score": 7.5, "warranty_months": 12,
    },
    {
        "brand": "Dell", "model_name": "XPS 13 Plus", "slug": "dell-xps-13-plus",
        "os": "windows", "form_factor": "ultrabook", "price_minor": 149_990_00,
        "cpu_score": 8_400, "ram_gb": 32, "weight_g": 1_260, "battery_minutes": 660,
        "screen_score": 9.4, "warranty_months": 24,
    },
    {
        "brand": "Xiaomi", "model_name": "RedmiBook 16", "slug": "xiaomi-redmibook-16",
        "os": "windows", "form_factor": "laptop", "price_minor": 63_990_00,
        "cpu_score": 5_100, "ram_gb": 16, "weight_g": 1_800, "battery_minutes": 540,
        "screen_score": 7.0, "warranty_months": 12,
    },
    {
        "brand": "MSI", "model_name": "Modern 15", "slug": "msi-modern-15",
        "os": "windows", "form_factor": "laptop", "price_minor": 72_990_00,
        "cpu_score": 6_100, "ram_gb": 16, "weight_g": 1_700, "battery_minutes": 420,
        "screen_score": 6.8, "warranty_months": 24,
    },
    {
        "brand": "Huawei", "model_name": "MateBook D 16", "slug": "huawei-matebook-d-16",
        "os": "windows", "form_factor": "laptop", "price_minor": 74_990_00,
        "cpu_score": 6_300, "ram_gb": 16, "weight_g": 1_680, "battery_minutes": 600,
        "screen_score": 7.2, "warranty_months": 12,
    },
    {
        "brand": "ASUS", "model_name": "TUF Gaming A15", "slug": "asus-tuf-gaming-a15",
        "os": "windows", "form_factor": "gaming", "price_minor": 109_990_00,
        "cpu_score": 9_100, "ram_gb": 16, "weight_g": 2_300, "battery_minutes": 300,
        "screen_score": 8.0, "warranty_months": 24,
    },
    {
        "brand": "Lenovo", "model_name": "ThinkPad E16", "slug": "lenovo-thinkpad-e16",
        "os": "windows", "form_factor": "laptop", "price_minor": 84_990_00,
        "cpu_score": 6_600, "ram_gb": 16, "weight_g": 1_900, "battery_minutes": 540,
        "screen_score": 6.9, "warranty_months": 36,
    },
    {
        "brand": "Apple", "model_name": "MacBook Pro 14 M3", "slug": "apple-macbook-pro-14-m3",
        "os": "macos", "form_factor": "laptop", "price_minor": 199_990_00,
        "cpu_score": 11_500, "ram_gb": 18, "weight_g": 1_600, "battery_minutes": 1_020,
        "screen_score": 9.6, "warranty_months": 12,
    },
    # Budget segment: keeps the 25–50k RUB range meaningful for students.
    {
        "brand": "Honor", "model_name": "MagicBook X 14", "slug": "honor-magicbook-x-14",
        "os": "windows", "form_factor": "laptop", "price_minor": 24_990_00,
        "cpu_score": 3_100, "ram_gb": 8, "weight_g": 1_380, "battery_minutes": 420,
        "screen_score": 5.8, "warranty_months": 12,
    },
    {
        "brand": "Acer", "model_name": "Aspire 3", "slug": "acer-aspire-3",
        "os": "windows", "form_factor": "laptop", "price_minor": 29_990_00,
        "cpu_score": 3_600, "ram_gb": 8, "weight_g": 1_900, "battery_minutes": 360,
        "screen_score": 5.5, "warranty_months": 12,
    },
    {
        "brand": "Xiaomi", "model_name": "RedmiBook 14", "slug": "xiaomi-redmibook-14",
        "os": "windows", "form_factor": "laptop", "price_minor": 32_990_00,
        "cpu_score": 3_900, "ram_gb": 8, "weight_g": 1_450, "battery_minutes": 450,
        "screen_score": 6.2, "warranty_months": 12,
    },
    {
        "brand": "Lenovo", "model_name": "V15 G4", "slug": "lenovo-v15-g4",
        "os": "windows", "form_factor": "laptop", "price_minor": 36_990_00,
        "cpu_score": 4_100, "ram_gb": 16, "weight_g": 1_700, "battery_minutes": 390,
        "screen_score": 5.9, "warranty_months": 12,
    },
    {
        "brand": "ASUS", "model_name": "VivoBook 15", "slug": "asus-vivobook-15",
        "os": "windows", "form_factor": "laptop", "price_minor": 44_990_00,
        "cpu_score": 4_600, "ram_gb": 16, "weight_g": 1_690, "battery_minutes": 450,
        "screen_score": 6.4, "warranty_months": 24,
    },
]
