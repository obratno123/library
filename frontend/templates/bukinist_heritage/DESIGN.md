# Design System Document: The Editorial Archive

## 1. Overview & Creative North Star: "The Digital Curator"
This design system moves away from the sterile, "plastic" feel of modern e-commerce and toward the tactile elegance of a high-end physical bookstore. Our Creative North Star is **"The Digital Curator."** 

We are not just building a shop; we are building an archive. The goal is to break the "template" look by using **intentional asymmetry**, where book covers are allowed to break the grid, and **high-contrast typography scales** that prioritize storytelling over simple data entry. By leveraging a "paper-on-paper" layering philosophy, we create an interface that feels organic, authoritative, and deeply intentional.

## 2. Colors & Surface Philosophy
The palette is rooted in warmth and intellectual depth. We avoid the "digital blue" and "hospital white" of standard UI, opting for a spectrum of creams and charred charcoals.

### The "No-Line" Rule
**Explicit Instruction:** Designers are prohibited from using 1px solid borders to define sections or cards. Boundaries must be defined solely through background color shifts. Use `surface-container-low` for a section sitting on a `surface` background to create a "recessed" or "elevated" feel without hard edges.

### Surface Hierarchy & Nesting
Treat the UI as a series of physical layers—like stacked sheets of fine Munken paper.
*   **Background (`#fbf9f4`):** The primary canvas.
*   **Surface-Container-Lowest (`#ffffff`):** Reserved for high-focus elements like the active book description or a shopping cart summary.
*   **Surface-Container-Highest (`#e4e2dd`):** Used for global navigation or footer areas to provide a grounded "weighted" feel.

### Signature Textures & Gradients
To provide visual "soul," avoid flat terracotta on large hero sections. Use a subtle linear gradient transitioning from `primary` (#8d4b00) to `primary_container` (#b15f00) at a 135-degree angle. This adds a "lithographic print" quality to the CTA buttons and banners.

## 3. Typography: The Editorial Voice
The system uses a tension between a sophisticated Serif and a functional Sans-serif to mimic the layout of a premium literary magazine.

*   **Display & Headlines (Newsreader):** Use these for book titles and section headers. The variable optical sizing of Newsreader allows for elegant, thin strokes at `display-lg` (3.5rem) that convey luxury.
*   **Interface & Prices (Manrope):** Use this for everything functional. Manrope’s geometric yet warm structure ensures that even small `label-sm` (0.6875rem) text remains legible.
*   **Hierarchy Note:** Always pair a `headline-lg` Serif with a `title-sm` Manrope sub-header in `on_surface_variant` (#554336) for an authoritative, curated look.

## 4. Elevation & Depth
We eschew traditional material shadows in favor of **Tonal Layering** and **Atmospheric Depth.**

*   **The Layering Principle:** Place a `surface_container_lowest` card on a `surface_container_low` section. The subtle contrast is enough for the human eye to perceive depth without the "noise" of shadows.
*   **Ambient Shadows:** If a floating element (like a quick-view book modal) is required, use a shadow with a blur of `32px`, a Y-offset of `8px`, and an opacity of `6%` using the `on_surface` color. It should feel like a soft glow of light, not a dark drop shadow.
*   **The "Ghost Border" Fallback:** If accessibility requires a container edge, use the `outline_variant` (#dbc2b0) at **15% opacity**. This creates a "watermark" effect rather than a structural line.
*   **Glassmorphism:** For the main navigation bar, use `surface` at 80% opacity with a `20px` backdrop-blur. This allows book covers to softly bleed through as the user scrolls, creating an integrated, immersive experience.

## 5. Components

### Buttons: The "Letterpress" Style
*   **Primary:** Background `primary` (#8d4b00), text `on_primary` (#ffffff). Shape: `md` (0.375rem). Use a subtle inner shadow (1px top-down) to simulate a letterpress effect.
*   **Tertiary:** No background. Use `primary` text with an underline that is 2px thick, offset by 4px.

### Cards: The Focus Element
*   **The Book Card:** Forbid the use of divider lines. Separate the book cover from the metadata using a `3` (1rem) spacing gap. The cover should have a `sm` (0.125rem) radius to mimic the hard edge of a book spine, while the container remains `none` (0px) to feel architectural.

### Input Fields: The "Clean Margin"
*   **Text Inputs:** Use `surface_container_high` as the fill. No border. On focus, transition the background to `surface_container_lowest` and add a `primary` "Ghost Border" (20% opacity).

### Chips & Filters
*   **Filter Chips:** Use `surface_container_low` with `label-md` Manrope text. When selected, shift to `secondary_container` (#fdbf8f) with `on_secondary_container` (#784c25) text.

## 6. Do’s and Don’ts

### Do:
*   **DO** use white space as a structural element. If a section feels crowded, increase spacing to `16` (5.5rem) rather than adding a divider line.
*   **DO** use "Breaking the Grid" techniques. Let high-quality book covers overlap the edge of a `surface_container` to create a 3D effect.
*   **DO** use `newsreader` for quotes or testimonials to add literary weight.

### Don’t:
*   **DON'T** use 100% black (#000000). Always use `on_surface` (#1b1c19) to maintain the "charcoal" softness.
*   **DON'T** use the `full` (9999px) roundedness on buttons. It feels too "app-like" and tech-focused. Stick to `md` (0.375rem) to maintain a classic aesthetic.
*   **DON'T** use standard grey icons. Icons should be tinted with `outline` (#887364) to feel part of the warm color story.