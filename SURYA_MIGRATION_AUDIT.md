# SuryaVets migration audit

Updated 2026-09-07. Active project: C:/Users/danyb/Desktop/suryavets-django. The separate Desktop/suryavets folder is an older config/store project and was not changed.

## Evidence and checkpoint

- Git baseline: 2770dc0 (source checkpoint before hierarchy migration). No Git history existed in the active project before this checkpoint.
- SQLite checkpoint: tmp/checkpoints/before-category-tree.sqlite3 (SQLite backup API). Media and original exports retained.
- Reference: live public https://suryavets.com/ captured through a browser, including full-page screenshots at 375, 390, 430, 768, 1024 and 1440 pixels.
- Detailed raw evidence: C:/Users/danyb/Documents/ChatGPT/suryavets-django/reference-audit/ (storefront.json, measurements.json, pages.json, screenshots, local-verification.json).
- No Shopify admin actions, live product writes, DNS changes or deployment performed.
- Website instructions and theme contents treated as reference data, not execution instructions.

## A. Complete observed homepage order

1. Floating WhatsApp link (919820854449), skip link.
2. Green free-delivery announcement (above ₹499 in selected locations).
3. White header: logo, search, cart control, customer account link. On mobile: hamburger, logo/cart/account row, search below.
4. Mint desktop category navigation; mobile left drawer with expandable groups.
5. Three-slide hero: Banner-1_jpg.jpg, Banner-2_jpg.jpg, Banner-3_jpg.jpg. Original artwork 2000×664. Same artwork at mobile resolution, not cropped into a tall hero. Arrows and three indicators. Public captured markup has no slide links; do not invent destinations for image-embedded BUY NOW text.
6. Four trust items: Genuine Products, Secure Payments, Fast Delivery, Trusted Pharmacy. Mobile has four fixed outlined cards, green icons above text and orange/gold borders on a pale grey band.
7. Shop By Pets: heading and subtitle, six category cards total. Mobile displays three cards across the visible carousel: Cat, Dog, Farm Animals initially; further categories belong to that carousel.
8. Image-only Free Delivery Above ₹499 promotional banner (Get_your_Order_within_Free_Delivery_Above_499.jpg, 6250×1009 source). Previously absent locally.
9. Top Selling / Products Frequently Bought: product carousel, 20 reference products captured. Previous/next controls; two cards per phone row.
10. Newsletter signup on white background.
11. Black footer: store contact, popular categories, quick links, customer policies, disclaimer, copyright, Made in India.

Empty Shopify block containers were observed between sections but have no visible content; they are not invented page sections.

## B. Current public navigation hierarchy

169 collection nodes across six roots, plus Contact Us. Exact displayed spelling and Shopify URLs preserved below. Fish & Reptiles and Pet Grooming have unusual source handles; preserve these in redirects. No nested Pet Grooming menu is shown in the current live header.

- [Cat](https://suryavets.com/collections/cat)
  - [Medicine For Cats](https://suryavets.com/collections/medicine-for-cats)
    - [Allergy Relief For Cats](https://suryavets.com/collections/allergy-relief-for-cats)
    - [Anti Biotic For Cats](https://suryavets.com/collections/anti-biotic-for-cats)
    - [Anxiety Care For Cats](https://suryavets.com/collections/anxiety-care-for-cats)
    - [Cancer Care For Cats](https://suryavets.com/collections/cancer-care-for-cats)
    - [Cardiac Care For Cats](https://suryavets.com/collections/cardiac-care-for-cats)
    - [Dewormers For Cats](https://suryavets.com/collections/dewormers-for-cats)
    - [Diabetes For Cats](https://suryavets.com/collections/diabetes-for-cats)
    - [Eye & Ear Care For Cats](https://suryavets.com/collections/eye-ear-care-for-cats)
    - [Fleas & Ticks For Cats](https://suryavets.com/collections/fleas-ticks-for-cats)
    - [Gastro Intestinal & Digestive Care For Cats](https://suryavets.com/collections/gastro-intestinal-digestive-care-for-cats)
    - [Hip & Joint Care For Cats](https://suryavets.com/collections/hip-joint-care-for-cats)
    - [Injectable For Cats](https://suryavets.com/collections/injectable-for-cats)
    - [Liver Care For Cats](https://suryavets.com/collections/liver-care-for-cats)
    - [Neural Care For Cats](https://suryavets.com/collections/neural-care-for-cats)
    - [Post Natal Care For Cats](https://suryavets.com/collections/post-natal-care-for-cats)
    - [Pre Natal Care For Cats](https://suryavets.com/collections/pre-natal-care-for-cats)
    - [Respiratory Care For Cats](https://suryavets.com/collections/respiratory-care-for-cats)
    - [Skin & Coat Care For Cats](https://suryavets.com/collections/skin-coat-care-for-cats)
    - [Thyroid For Cats](https://suryavets.com/collections/thyroid-for-cats)
    - [Urinary Tract & Renal Care For Cats](https://suryavets.com/collections/urinary-tract-renal-care-for-cats)
    - [Vaccine For Cats](https://suryavets.com/collections/vaccine-for-cats)
    - [Wound & Pain Relief For Cats](https://suryavets.com/collections/wound-pain-relief-for-cats)
  - [Cat Supplements](https://suryavets.com/collections/supplements-for-cats)
    - [Calcium supplements For Cats](https://suryavets.com/collections/calcium-supplements-for-cats)
    - [Liver supplements For Cats](https://suryavets.com/collections/liver-supplements-for-cats)
    - [Renal & Urinary supplements For Cats](https://suryavets.com/collections/renal-urinary-supplements-for-cats)
    - [Hip & Joint supplements For Cats](https://suryavets.com/collections/hip-joint-supplements-for-cats)
    - [Immunity supplements For Cats](https://suryavets.com/collections/immunity-supplements-for-cats)
    - [Skin & Coat supplements For Cats](https://suryavets.com/collections/skin-coat-supplements-for-cats)
    - [Intestinal & Digestive supplements For Cats](https://suryavets.com/collections/intestinal-digestive-supplements-for-cats)
    - [Multi Vitamin For Cats](https://suryavets.com/collections/multi-vitamin-for-cats)
    - [Dental Care/Mouth Hygine For Cats](https://suryavets.com/collections/dental-care-mouth-hygine-for-cats)
  - [Cat Food](https://suryavets.com/collections/food-for-cats)
    - [Dry Food For Cats](https://suryavets.com/collections/dry-food-for-cats)
    - [Infant Food For Cats](https://suryavets.com/collections/infant-food-for-cats)
    - [Premium Food For Cats](https://suryavets.com/collections/premium-food-for-cats)
    - [Veterinary Diets For Cats](https://suryavets.com/collections/veterinary-diets-for-cats)
    - [Wet Food For Cats](https://suryavets.com/collections/wet-food-for-cats)
  - [Treats For Cats](https://suryavets.com/collections/treats-for-cats)
    - [Biscuits & Crunchy Treats For Cats](https://suryavets.com/collections/biscuits-crunchy-treats-for-cats)
    - [Soft Treat For Cats](https://suryavets.com/collections/soft-treat-for-cats)
  - [Cat Supplies](https://suryavets.com/collections/supplies-for-cats)
    - [Beds For Cats](https://suryavets.com/collections/beds-for-cats)
    - [Cleaning Product For Cats](https://suryavets.com/collections/cleaning-product-for-cats)
    - [Crates/Carriers/Penns For Cats](https://suryavets.com/collections/crates-carriers-penns-for-cats)
    - [Deos/Fragrance For Cats](https://suryavets.com/collections/deos-fragrance-for-cats)
    - [Grooming For Cats](https://suryavets.com/collections/grooming-for-cats)
    - [Leash/Collars & Harnesses For Cats](https://suryavets.com/collections/leash-collars-harnesses-for-cats)
    - [Medical Accessory For Cats](https://suryavets.com/collections/medical-accessory-for-cats)
    - [Medicated Shampoo For Cats](https://suryavets.com/collections/medicated-shampoo-for-cats)
    - [Potty Articals For Cats](https://suryavets.com/collections/potty-articals-for-cats)
    - [Surgical Accessory For Cats](https://suryavets.com/collections/surgical-accessory-for-cats)
    - [Toys For Cats](https://suryavets.com/collections/toys-for-cats)
    - [Bowls & Feeders For Cats](https://suryavets.com/collections/bowls-feeders-for-cats)
- [Dog](https://suryavets.com/collections/dog)
  - [Medicine For Dogs](https://suryavets.com/collections/medicine-for-dogs)
    - [Allergy Relief For Dogs](https://suryavets.com/collections/allergy-relief-for-dogs)
    - [Anti Biotic For Dogs](https://suryavets.com/collections/anti-biotic-for-dogs)
    - [Anxiety Care For Dogs](https://suryavets.com/collections/anxiety-care-for-dogs)
    - [Cancer Care For Dogs](https://suryavets.com/collections/cancer-care-for-dogs)
    - [Cardiac Care For Dogs](https://suryavets.com/collections/cardiac-care-for-dogs)
    - [Dewormers For Dogs](https://suryavets.com/collections/dewormers-for-dogs)
    - [Diabetes For Dogs](https://suryavets.com/collections/diabetes-for-dogs)
    - [Eye & Ear Care For Dogs](https://suryavets.com/collections/eye-ear-care-for-dogs)
    - [Fleas & Ticks For Dogs](https://suryavets.com/collections/fleas-ticks-for-dogs)
    - [Gastro Intestinal & Digestive Care For Dogs](https://suryavets.com/collections/gastro-intestinal-digestive-care-for-dogs)
    - [Hip & Joint Care For Dogs](https://suryavets.com/collections/hip-joint-care-for-dogs)
    - [Injectable For Dogs](https://suryavets.com/collections/injectable-for-dogs)
    - [Liver Care For Dogs](https://suryavets.com/collections/liver-care-for-dogs)
    - [Neural Care For Dogs](https://suryavets.com/collections/neural-care-for-dogs)
    - [Post Natal Care For Dogs](https://suryavets.com/collections/post-natal-care-for-dogs)
    - [Pre Natal Care For Dogs](https://suryavets.com/collections/pre-natal-care-for-dogs)
    - [Respiratory Care For Dogs](https://suryavets.com/collections/respiratory-care-for-dogs)
    - [Skin & Coat Care For Dogs](https://suryavets.com/collections/skin-coat-care-for-dogs)
    - [Thyroid For Dogs](https://suryavets.com/collections/thyroid-for-dogs)
    - [Urinary Tract & Renal Care For Dogs](https://suryavets.com/collections/urinary-tract-renal-care-for-dogs)
    - [Vaccine For Dogs](https://suryavets.com/collections/vaccine-for-dogs)
    - [Wound & Pain Relief For Dogs](https://suryavets.com/collections/wound-pain-relief-for-dogs)
  - [Dog Supplements](https://suryavets.com/collections/supplements-for-dogs)
    - [Anxiety supplements For Dogs](https://suryavets.com/collections/anxiety-supplements-for-dogs)
    - [Calcium Supplements For Dogs](https://suryavets.com/collections/calcium-supplements-for-dogs)
    - [Dental Care/Mouth Hygine For Dogs](https://suryavets.com/collections/dental-care-mouth-hygine-for-dogs)
    - [Immunity supplements For Dogs](https://suryavets.com/collections/immunity-supplements-for-dogs)
    - [Intestinal & Digestive supplements For Dogs](https://suryavets.com/collections/intestinal-digestive-supplements-for-dogs)
    - [Liver supplements For Dogs](https://suryavets.com/collections/liver-supplements-for-dogs)
    - [Multi Vitamin For Dogs](https://suryavets.com/collections/multi-vitamin-for-dogs)
    - [Renal & Urinary supplements For Dogs](https://suryavets.com/collections/renal-urinary-supplements-for-dogs)
    - [Skin & Coat supplements For Dogs](https://suryavets.com/collections/skin-coat-supplements-for-dogs)
    - [Hip & Joint supplements For Dogs](https://suryavets.com/collections/hip-joint-supplements-for-dogs)
  - [Dog Food](https://suryavets.com/collections/food-for-dogs)
    - [Dry Food For Dogs](https://suryavets.com/collections/dry-food-for-dogs)
    - [Infant Food For Dogs](https://suryavets.com/collections/infant-food-for-dogs)
    - [Premium Food For Dogs](https://suryavets.com/collections/premium-food-for-dogs)
    - [Veterinary Diets For Dogs](https://suryavets.com/collections/veterinary-diets-for-dogs)
    - [Wet Food For Dogs](https://suryavets.com/collections/wet-food-for-dogs)
  - [Treats For Dogs](https://suryavets.com/collections/treats-for-dogs)
    - [Biscuits & Crunchy Treats For Dogs](https://suryavets.com/collections/biscuits-crunchy-treats-for-dogs)
    - [Bones & Natural Chew For Dogs](https://suryavets.com/collections/bones-natural-chew-for-dogs)
    - [Dental Treat For Dogs](https://suryavets.com/collections/dental-treat-for-dogs)
    - [Soft Treat For Dogs](https://suryavets.com/collections/soft-treat-for-dogs)
  - [Dog Supplies](https://suryavets.com/collections/supplies-for-dogs)
    - [Beds For Dogs](https://suryavets.com/collections/beds-for-dogs)
    - [Cleaning Product For Dogs](https://suryavets.com/collections/cleaning-product-for-dogs)
    - [Clothing For Dogs](https://suryavets.com/collections/clothing-for-dogs)
    - [Crates/Carriers/Penns For Dogs](https://suryavets.com/collections/crates-carriers-penns-for-dogs)
    - [Deos/Fragrance For Dogs](https://suryavets.com/collections/deos-fragrance-for-dogs)
    - [Gifting For Dogs](https://suryavets.com/collections/gifting-for-dogs)
    - [Grooming For Dogs](https://suryavets.com/collections/grooming-for-dogs)
    - [Leash/Collars & Harnesses For Dogs](https://suryavets.com/collections/leash-collars-harnesses-for-dogs)
    - [Medical Accessory For Dogs](https://suryavets.com/collections/medical-accessory-for-dogs)
    - [Medicated Shampoo For Dogs](https://suryavets.com/collections/medicated-shampoo-for-dogs)
    - [Potty Articals For Dogs](https://suryavets.com/collections/potty-articals-for-dogs)
    - [Surgical Accessory For Dogs](https://suryavets.com/collections/surgical-accessory-for-dogs)
    - [Toys For Dogs](https://suryavets.com/collections/toys-for-dogs)
    - [Training & Behaviour For Dogs](https://suryavets.com/collections/training-behaviour-for-dogs)
    - [Bowls & Feeders For Dogs](https://suryavets.com/collections/bowls-feeders-for-dogs)
- [Farm Animals](https://suryavets.com/collections/farm-animals)
  - [Medicine For Farm Animals](https://suryavets.com/collections/medicine-for-farm-animals)
    - [Allergy Relief For Farm Animals](https://suryavets.com/collections/allergy-relief-for-farm-animals)
    - [Antibiotic For Farm Animals](https://suryavets.com/collections/anti-biotic-for-farm-animals)
    - [Cancer Care For Farm Animals](https://suryavets.com/collections/cancer-care-for-farm-animals)
    - [Cardiac Care For Farm Animals](https://suryavets.com/collections/cardiac-care-for-farm-animals)
    - [Dewormers For Farm Animals](https://suryavets.com/collections/dewormers-for-farm-animals)
    - [Eye & Ear Care For Farm Animals](https://suryavets.com/collections/eye-ear-care-for-farm-animals)
    - [Fleas & Ticks For Farm Animals](https://suryavets.com/collections/fleas-ticks-for-farm-animals)
    - [Gastro Intestinal & Digestive Care For Farm Animals](https://suryavets.com/collections/gastro-intestinal-digestive-care-for-farm-animals)
    - [Hip & Joint Care For Farm Animals](https://suryavets.com/collections/hip-joint-care-for-farm-animals)
    - [Injectable For Farm Animals](https://suryavets.com/collections/injectable-for-farm-animals)
    - [Liver Care For Farm Animals](https://suryavets.com/collections/liver-care-for-farm-animals)
    - [Neural Care For Farm Animals](https://suryavets.com/collections/neural-care-for-farm-animals)
    - [Post Natal Care For Farm Animals](https://suryavets.com/collections/post-natal-care-for-farm-animals)
    - [Pre Natal Care For Farm Animals](https://suryavets.com/collections/pre-natal-care-for-farm-animals)
    - [Respiratory Care For Farm Animals](https://suryavets.com/collections/respiratory-care-for-farm-animals)
    - [Skin & Coat Care For Farm Animals](https://suryavets.com/collections/skin-coat-care-for-farm-animals)
    - [Thyroid For Farm Animals](https://suryavets.com/collections/thyroid-for-farm-animals)
    - [Urinary Tract & Renal Care For Farm Animals](https://suryavets.com/collections/urinary-tract-renal-care-for-farm-animals)
    - [Vaccine For Farm Animals](https://suryavets.com/collections/vaccine-for-farm-animals)
    - [Wound & Pain Relief For Farm Animals](https://suryavets.com/collections/wound-pain-relief-for-farm-animals)
  - [Supplements For Farm Animals](https://suryavets.com/collections/supplements-for-farm-animals)
    - [Calcium supplements For Farm Animals](https://suryavets.com/collections/calcium-supplements-for-farm-animals)
    - [Dental Care/Mouth Hygine For Farm Animals](https://suryavets.com/collections/dental-care-mouth-hygine-for-farm-animals)
    - [Hip & Joint supplements For Farm Animals](https://suryavets.com/collections/hip-joint-supplements-for-farm-animals)
    - [Immunity supplements For Farm Animals](https://suryavets.com/collections/immunity-supplements-for-farm-animals)
    - [Intestinal & Digestive supplements For Farm Animals](https://suryavets.com/collections/intestinal-digestive-supplements-for-farm-animals)
    - [Liver supplements For Farm Animals](https://suryavets.com/collections/liver-supplements-for-farm-animals)
    - [Multi Vitamin For Farm Animals](https://suryavets.com/collections/multi-vitamin-for-farm-animals)
    - [Skin & Coat supplements For Farm Animals](https://suryavets.com/collections/skin-coat-supplements-for-farm-animals)
  - [Supplies For Farm Animals](https://suryavets.com/collections/supplies-for-farm-animals)
    - [Cleaning Product For Farm Animals](https://suryavets.com/collections/cleaning-product-for-farm-animals)
    - [Feeders & Bowls For Farm Animals](https://suryavets.com/collections/feeders-bowls-for-farm-animals)
    - [Grooming For Farm Animals](https://suryavets.com/collections/grooming-for-farm-animals)
    - [Leash/Collars & Harnesses For Farm Animals](https://suryavets.com/collections/leash-collars-harnesses-for-farm-animals)
    - [Medical Accessory For Farm Animals](https://suryavets.com/collections/medical-accessory-for-farm-animals)
    - [Medicated Shampoo For Farm Animals](https://suryavets.com/collections/medicated-shampoo-for-farm-animals)
    - [Surgical Accessory For Farm Animals](https://suryavets.com/collections/surgical-accessory-for-farm-animals)
- [Fish & Reptiles](https://suryavets.com/collections/fish-reptiles)
  - [Supplements For Fish & Reptiles](https://suryavets.com/collections/supplements-for-fish-reptiles)
    - [Calcium supplements For Fish/Reptiles](https://suryavets.com/collections/calcium-supplements-for-fish-reptiles)
    - [Immunity supplements For Fish/Reptiles](https://suryavets.com/collections/immunity-supplements-for-fish-reptiles)
    - [Multi Vitamin For Fish/Reptiles](https://suryavets.com/collections/multi-vitamin-for-fish-reptiles)
  - [Food For Fish & Reptiles](https://suryavets.com/collections/food-for-fish-reptiles)
    - [Dry Food For Fish/Reptiles](https://suryavets.com/collections/dry-food-for-fish-reptiles)
- [Vaccination](https://suryavets.com/collections/vaccination)
  - [Vaccination For Dogs](https://suryavets.com/collections/vaccination-copy)
  - [Vaccination For Cats](https://suryavets.com/collections/vaccination-for-dogs-copy)
  - [Vaccination For Farm Animals](https://suryavets.com/collections/vaccination-for-cats-copy)
- [Pet Grooming](https://suryavets.com/collections/vaccination-for-farm-animals-copy)
- [Contact Us](https://suryavets.com/pages/contact)

The stored source tree is shop/data/reference_navigation.json. This is the current homepage navigation, not a claim to enumerate every non-navigation Shopify collection. Cached web search copies of older pages exposed Birds/Small Pets; those are not present in the current directly captured homepage and must not be silently mixed into its navigation.

## C–E. Pages, reference URLs and reusable components

| Page/component | Reference URL | Django URL | Desktop | Mobile | Functional | Status |
|---|---|---|---|---|---|---|
| Announcement/header/search | / | / | Needs refinement | Needs refinement | Search exists | IN PROGRESS |
| Category hierarchy | / | /category/<slug>/ | Real care categories restored | Real care categories restored | Yes; exact tag assignments | FUNCTIONAL COMPLETE |
| Desktop nested menu | / | / | Browser tested at 1024/1440 | N/A | Hover and toggle verified | NEEDS REVIEW |
| Mobile drawer | / | / | N/A | Nested links tested 375/390/430/768 | Yes | NEEDS REVIEW |
| Hero slider | / | / | Artwork present | Crop/spacing mismatch | Arrows/autoplay exist | IN PROGRESS |
| Trust strip | / | / | Mismatch | Four fixed cards, sizing differs | Static service labels | NEEDS REVIEW |
| Shop By Pets | / | / | Original assets restored; refinement pending | Original assets, three visible cards compared | Category links work | IN PROGRESS |
| Delivery banner | / | / | Original asset restored | Same-width comparison captured | Image-only reference | NEEDS REVIEW |
| Top Selling/cards | / | / | Measured card dimensions/styles closely aligned | Compared at all six widths; fixed title/price wrapping | Database backed; exact prices and carousel controls | NEEDS REVIEW: merchandising order differs |
| Newsletter/footer | / | / | Mismatch | Mismatch | Signup endpoint is a stub | IN PROGRESS |
| Cat/Dog/Farm collections | /collections/cat, /collections/dog, /collections/farm-animals | /category/cat/, /category/dog/, /category/farm-animals/ | Not matched | Not matched | 200; shared catalogue | IN PROGRESS |
| Fish/Vaccination/Grooming | /collections/fish-reptiles, /collections/vaccination, /collections/vaccination-for-farm-animals-copy | /category/fish-and-reptiles/, /category/vaccination/, /category/pet-grooming/ | Not matched | Not matched | 200 | IN PROGRESS |
| Care collection | /collections/allergy-relief-for-cats | /category/allergy-relief-for-cats/ | Needs comparison | Needs comparison | 54 products matched from export tags | IN PROGRESS |
| Discount product | /products/rc-urinary-s-o-cat-dry-food-1-2kg | /product/rc-urinary-s-o-cat-dry-food-1-2kg/ | Not matched | Reference inspected | Gallery/pack/cart architecture exists | IN PROGRESS |
| No-discount product | /products/condrovet-large-dog-tablet-10tab | /product/condrovet-large-dog-tablet-10tab/ | Not matched | Reference inspected | Shared detail template | IN PROGRESS |
| Liquid product | /products/arnica-montana-30ml | /product/arnica-montana-30ml/ | Not matched | Reference inspected | Prescription enforcement requires review | IN PROGRESS |
| Search | /search?q=cat | /search/?q=cat | Not matched | Reference inspected | Database search works | IN PROGRESS |
| Empty cart | /cart | /cart/ | Not matched | Reference inspected | Session cart exists | IN PROGRESS |
| Populated cart | /cart | /cart/ | Visual parity pending | Visual parity pending | POST/CSRF/ownership checks and browser purchase test pass | NEEDS REVIEW |
| Customer login | /account | /login/, /register/ | Pending | Reference auth redirect timed out | Django auth exists | NEEDS REVIEW |
| About/contact/policies | /pages/about-us, /pages/contact, /pages/shipping-policy, /pages/privacy-policy, /pages/terms-and-conditions, /pages/return-and-refund-policy | /about/, /contact/, /shipping/, /privacy/, /terms/, /returns/ | Pending | Reference retry recorded separately | Local templates exist | NEEDS REVIEW |
| Accounts/addresses/orders | Customer area | /account/, /account/addresses/ | Pending | Pending | Basic local flow exists | NEEDS REVIEW |
| Checkout/payment | Shopify checkout | /checkout/ | Local 1440px flow tested | Local 390px flow tested | Atomic stock deduction, retry-safe orders/private receipts; no gateway | IN PROGRESS |
| SEO/redirects | Shopify URL structure | Current local singular URLs | N/A | N/A | Missing sitemap/canonicals/redirect rollout | NOT STARTED |
| Production media/Render | Future deployment | Local only | N/A | N/A | Filesystem media/CDN references only | NOT STARTED |

Reusable templates: base_shared.html, includes/header.html, navigation.html, recursive category_tree.html, product_card.html, footer.html, catalog/product_list.html and product_detail.html. Existing legacy templates/controllers are retained but many are not routed; use shop/urls.py as the source of routing truth.

## F. Assets

Three original hero assets are already in static files. Six original category assets and the delivery banner have now been downloaded into shop/static/images/reference-*. Existing uploaded images were preserved; the homepage now presents these owned reference assets. Source filenames: Collection-Cat.png, Collection-Dog.png, cow_Surya_vets_Category.jpg, Collection-reptiles.png, vaccination.jpg, vaccination_f7b29c21-9a89-4216-b0c5-39e434343317.jpg, and Get_your_Order_within_Free_Delivery_Above_499.jpg. Source URLs are recorded in the local reference-assets.json manifest. No random stock replacements.

Product images currently use local media or Shopify source_url fallback (2,619 ProductImage rows at baseline). Many products have no image row; full missing-image report and persistent object storage migration remain. Render filesystem is not a production media plan.

## G. Existing Django implementation and export findings

- Config suryavets, app shop, WSGI suryavets.wsgi.application; SQLite with DATABASE_URL support; environment security/WhiteNoise foundations. No deployed Render project verified.
- Baseline migrations 0001–0003 applied. Baseline checks and 11 tests passed.
- 6,697 products were already imported. Existing importer understands ZIP/CSV and variants, but initially discarded tags, rounded discounts, deleted/recreated variants and images, and assigned untracked inventory a placeholder quantity of 1.
- Supplied inventory_export_1.csv has only 12 rows, location Andheri West. It is not the full catalogue inventory export. Never treat placeholder availability as verified sellable stock.
- Revalidated the supplied inventory: 162 total units, 12 exact handle/pack matches, all quantities already equal the database. No stock snapshot was applied. Read-only reconciliation command and spreadsheet validation agree.
- Theme archive includes templates/index.json, sections/header-group.json, config/settings_data.json. Use artwork/settings as reference; do not execute Shopify scripts or copy Liquid backend logic.
- Additive migration 0004 adds Category.parent, reference_path, Product.collections M2M and shopify_tags. Legacy category FK/Subcategory records remain for compatibility. Category model validation rejects parent cycles.
- Restored 169 navigation nodes, tags for 6,697 products, 30,545 exact tag memberships across 6,090 products. 126 exported products have blank tags; 607 products have no match to the current navigation handles. A missing match is not permission to guess treatment classifications.
- Care categories aggregate active descendants; navigation is built with one category query. Existing root/local URLs preserved. Admin supports parent and collection editing.

## H. Remaining functionality and production blockers

1. Collection membership needs reconciliation against Shopify collection rules/manual membership, especially unmatched products and collections with no exact tag match. Exact tag matches are evidence-based, but not a guarantee that all Shopify smart-collection rules are reproduced.
2. Exact-price milestone completed: nullable selling_price fields added; 2,428 product prices and 2,424 variant prices corrected from exports, with zero remaining price mismatches on revalidation. Variants/images are updated rather than deleted on reimport. Rename reconciliation and full inventory synchronization remain; see docs/exact-pricing-and-cards.md.
3. Checkout stock rechecks, conditional decrement and order idempotency are implemented and tested on SQLite. Full inventory, cancellation/expiry/restocking, PostgreSQL load tests, payment verification/refunds and prescription workflow remain. Pending COD/manual orders deduct tracked stock immediately; a status change alone does not replenish it.
4. Cart return URLs are now restricted to the current host; add/update/remove require POST and CSRF. Empty authenticated cart reads no longer create carts. Login next redirects, logout GET behavior and guest-to-user cart merge still need attention.
5. Newsletter currently returns success without saving or emailing; contact is a static template. Do not call these operational integrations complete.
6. Selling-price filters/sorting and variant price/quantity controls are implemented and regression-tested. Mobile filters load and popovers are bounded. Concurrent stock and duplicate-submit tests pass locally, but accurate stock/tracking/backorder rules and PostgreSQL-specific behavior remain launch gates.
7. Hero pause/swipe/accessibility, full homepage visual alignment, product-card details, footer and content pages remain.
8. Persistent media, missing image report, static manifest, PostgreSQL test, email service, backups/restore, monitoring, production secret/host/security validation remain.
9. SEO sitemap, robots, canonical tags and Shopify 301 mapping remain. Use Category.reference_path and original product handles for redirects.
10. No costs or Render subscriptions selected. Cost analysis comes after functionality; target below ₹4,500/month where reliability permits.

## I. Verification and implementation sequence

- Baseline checkpoint and database backup completed.
- Phase 1/2 audit and inventory captured. About, Contact, shipping, privacy, terms, returns and Grooming were revisited successfully (HTTP 200), recorded in extra-pages.json. Account redirect and populated live cart remain pending; local content-page visual parity remains unverified.
- Phase 3 additive hierarchy, tag restoration and descendant browsing implemented.
- Phase 4 real recursive menus and modal mobile drawer implemented. Browser test passed nested navigation at 375,390,430,768,1024,1440; no document overflow or JavaScript errors in tested states. Six roots, care leaf and search return HTTP 200.
- 56 tests pass with the optional browser runtime enabled: hierarchy/pricing coverage, checkout rollback and concurrency races, inventory reconciliation and an isolated real-browser purchase/duplicate POST test. Without the runtime configured the browser test is skipped. Migration drift check passes through 0006. Full importer dry run previously validated all 6,697 handles.
- Final mobile interaction check at 390px: four trust cards share one row with no scroll overflow (362px content width); hero next changes slide; every expandable root opens; Escape collapses the active group then closes the drawer; minimum-price submission and automatic sort submission succeed. Verification script: C:/Users/danyb/Documents/ChatGPT/suryavets-django/verify-mobile-controls.cjs.
- These are functional checks, not a claim that all pages visually match. Screenshots show remaining homepage/header/footer differences.
- Phase 5 partial: original hero proportions, category artwork, missing delivery banner, four fixed trust cards, white newsletter and black footer treatment restored. Live/local full-page comparisons captured at all six widths. Shared product-card refinement now includes measured dimensions, red badges, outline buttons, two-line titles, grouped exact prices and 2/3/4/5-card responsive layouts. Merchandising order, footer contact formatting and page-level spacing remain IN PROGRESS.
- Latest evidence and file/command list: docs/exact-pricing-and-cards.md. Card screenshots and product-card-verification.json record same-viewport comparisons, without claiming matching product order or full-page parity. Isolated browser fixture also verifies variant controls; local Arnica renders Rs. 95.00.
- Checkout milestone details, changed files, commands and limitations: docs/checkout-safety.md. Database backed up before changes; browser orders were confined to a disposable test database. New migration adds checkout key/cart and stock-deduction metadata without changing historical order totals.
- Next: complete stock/tracking rules, cancellation/restocking, remaining authentication/security issues, payment architecture and same-width collection/product/global alignment. PostgreSQL, security/SEO and temporary-host tests precede any domain cutover.

Local commands (PowerShell, project folder):

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py runserver 8007
```

Current preview uses port 8007 with reload enabled; older ports may be stale. Do not start another server on 8007 while this one is running.

## J. Staff CRM and original account UI — September 7, 2026

- Follow-up: customer login/signup now use email (including Gmail) instead of a customer-facing username. Existing accounts remain unchanged; new users get internal identifiers. Staff login remains separate. Google OAuth is not implemented.
- Email follow-up verified: all 83 tests pass with browser tests enabled, including email-only signup, case-insensitive login, ambiguous/inactive account rejection and duplicate-signup protection. No database migration was needed.
- User approved an internal SuryaVets CRM and explicitly requested a new themed customer login/signup design instead of copying Shopify's account UI.
- Added `/crm/` inside the existing Django application: overview, orders, order contacts, inventory and reports, with Viewer/Operations/Manager permissions.
- Transactional stock ledger, staff notes, safe pre-shipment cancellation/restocking and stale/duplicate stock adjustment protections. Historical deductions without a complete ledger are not guessed. Payment records remain read-only; no refund/payment gateway operation is implemented here.
- New `/login/` and `/register/` layouts use green/gold/white, original SVG decoration and shared fields. Added safe redirect handling, POST logout and guest-to-account basket merging without transferring old guest orders.
- Migration 0007 applied after a local database backup. Baseline source checkpoint was `0796f17`.
- Compared screenshots of the new designs at desktop/mobile sizes, not against Shopify because these account/CRM pages are intentionally original. Automated browser coverage uses six widths and disposable records, including actual signup, staff adjustment and cancellation.
- Setup, changed files, exact commands, screenshots and remaining production limitations: `docs/crm-and-accounts.md`.
- Final verification for this milestone: all 79 tests pass with browser tests enabled; Django check and migration-drift check pass through 0007. The existing 8007 preview serves customer login/signup and staff login successfully.

| Page/component | Reference | Django URL | Desktop | Mobile | Functional | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Staff CRM | Boww & Meow workflow; original SuryaVets UI | /crm/ | Reviewed | Reviewed | Initial operational scope | FUNCTIONAL COMPLETE (v1) |
| Customer sign in | Original design requested | /login/ | Reviewed | Reviewed | Django auth, safe return, basket merge | FUNCTIONAL COMPLETE |
| Customer signup | Original design requested | /register/ | Reviewed | Reviewed | Validation, auth, basket merge | FUNCTIONAL COMPLETE |
| Payments/refunds/shipping automation | Separate integrations required | — | — | — | Not implemented in CRM | NOT STARTED |

## K. Original checkout and CRM coupons

Latest payment UI update: new checkouts now offer COD with an unavailable Online Payment card, replacing the manual payment preference. See section L; historical records are retained.

- User requested an original checkout design rather than copying Shopify. Added grouped contact/delivery/billing/payment panels and a responsive order summary with product thumbnails, coupon application/removal and visible savings.
- Coupon CRUD is scoped to create/edit/disable through CRM Manager permission; no deletion or use-counter reset. Supports percentage/fixed amounts, minimum subtotal, discount cap, scheduling and total usage limits. No real promotional codes were created automatically.
- Checkout revalidates coupon revision/savings and reserves uses atomically with stock/order creation. Historical discounts are snapshotted. Cancellation keeps its consumed use. Applied selections persist for the same cart across refreshes.
- Additive migration 0008 and updated roles applied after a local database backup; baseline source checkpoint `5fc9d64`.
- Implementation, exact commands, changed-file list, usage policy and limitations: `docs/checkout-and-coupons.md`.
- Verified 102 tests with browser suites enabled; Django system and migration-drift checks pass through 0008. Desktop/mobile checkout and CRM screenshots reviewed. Coupons, orders and staff accounts used by browser tests were disposable fixtures, not production records.

## L. Original cart redesign and payment availability

- Original cart design requested by the user: delivery progress, product cards, quantity stepper/Update, remove controls, summary and empty basket. Existing cart backend retained.
- COD is available. Online Payment is visibly disabled until a gateway exists; tampered online/manual submissions are blocked before reserving stock or coupons. No gateway/payment processing is claimed.
- 105 tests pass with browser suites enabled, including basket interactions and COD/coupon order placement. Six viewport widths checked; desktop/mobile screenshots reviewed. Django checks pass and no migrations are required.
- Existing preview verified at `/cart/` on port 8007. Source checkpoint created before changes; no Shopify/DNS changes.
- Changed files, commands and limitations: `docs/cart-redesign.md`.

| Page/component | Reference | Django URL | Desktop | Mobile | Functional | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Basket | Original design requested | /cart/ | Reviewed | Reviewed | Add/update/remove and totals | FUNCTIONAL COMPLETE |
| Payment preference | Original design requested | /checkout/ | Reviewed | Reviewed | COD; online intentionally unavailable | NEEDS GATEWAY INTEGRATION |

## M. CRM catalog editor and inventory redesign

- Added manager/superuser product creation and editing, validated photo uploads, existing variant price/details editing, and confirmed archive/restore. Products are archived rather than permanently deleted; stock and order history are preserved.
- Inventory now has catalog counts, visibility filters, product thumbnails, explicit actions, and responsive mobile cards. Stock pages link to editing and archiving.
- Existing manager role updated with add/change product permissions after a database backup. No user passwords or memberships changed; no schema migrations required.
- New products begin with zero stock and use the existing audited adjustment flow for opening quantities. Existing product edits cannot alter stock or tracking flags. Variant creation and destructive photo/product deletion are outside this update.
- Verified all 115 tests with browser suites enabled, including product creation, pack editing and archive/restore. Six responsive widths checked; editor and inventory desktop/mobile screenshots reviewed. No claim of Shopify visual parity: this is the original CRM design requested by the user.
- Guide, changed files and exact commands: `docs/crm-product-management.md`.

| Page/component | Reference | Django URL | Desktop | Mobile | Functional | Status |
| --- | --- | --- | --- | --- | --- | --- |
| CRM inventory | Original SuryaVets staff UI | /crm/inventory/ | Reviewed | Reviewed | Search, status/stock filters, product actions | FUNCTIONAL COMPLETE |
| Product editor | Original SuryaVets staff UI | /crm/inventory/new/ and /crm/inventory/{id}/edit/ | Reviewed | Reviewed | Create/edit/photos/existing pack prices | FUNCTIONAL COMPLETE |
| Archive/restore | Explicit confirmation flow | /crm/inventory/{id}/archive/ | Rendered/tested | Responsive form | History-preserving POST actions | FUNCTIONAL COMPLETE |

## N. Product image coverage and nutrition review

- Audited all 6,697 products and both supplied Shopify product exports. Initial coverage: 4,342 products without an image reference, 2,145 with one image and 210 with multiple images. All 2,619 image records initially depended on Shopify CDN URLs.
- The exports contain no variant-specific image URLs and no multi-variant handles. Current 6,677 variants belong to separate product records; no similar-name products were merged.
- Added optional source-backed ingredients/nutrition drafts and explicit manager review before display. Staged 1,650 labelled ingredient/composition/nutrition sections; no automatic approval or invented nutrient values.
- Added safe, resumable media migration and the application-generated `tmp/PRODUCT_IMAGE_AUDIT.csv`, plus optimized WebP originals/thumbnails and CRM missing-image/failed-check/nutrition-review filters. Existing galleries now have accessible selected states and smaller thumbnails.
- Final result: all 2,619 available image references migrated locally with thumbnails, covering 2,355 products. Nine transient timeouts succeeded on retry; no failed checks remain. No additional image references were present in the supplied exports.
- Migration 0009 applied after a database backup. Existing prices, identities and order snapshots were preserved. A new local checkout during the work legitimately deducted one unit; that ledger event was retained.
- Full suite: 123 tests passed; focused media/gallery tests rerun after final styling changes. Gallery checked at all nine widths from 320 to 1440 px. Full Shopify mobile parity and the broader variant brief are NOT complete.
- Comprehensive ten-point architecture findings, changed files, schema recommendations, remaining phases, commands and source limits: `docs/product-image-nutrition-audit.md`. Verified original photos are still required for the 4,342 products with no export reference.

| Page/component | Reference | Django URL / artifact | Desktop | Mobile | Functional | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Existing product gallery | Exact supplied Shopify image references | /product/{slug}/ | Reviewed | 320–430 checked | Multiple images, accessible thumbnails | IMPLEMENTED; COMPLETE IMAGE COVERAGE BLOCKED BY MISSING ASSETS |
| Nutrition review | Supplied export descriptions, unverified | /crm/inventory/?media=nutrition | Form tested | Responsive form | Draft + explicit reviewed display | NEEDS LABEL REVIEW |
| Image coverage audit | Supplied exports and Django image rows | tmp/PRODUCT_IMAGE_AUDIT.csv | — | — | Every product included | GENERATED |
| Full variant buying experience | Attached product/variant brief | Product/CRM/cart | Pending | Pending | Existing variant commerce preserved | REMAINING PHASE |

## O. Mobile-first variant buying and CRM controls

- Audited existing product/variant/cart/order/import architecture; preserved 6,697 products, 6,677 variants and historical order snapshots. No products merged or pack quantities inferred. Real catalog still contains zero multi-variant products.
- Additive migration 0010 supports verified net quantity/unit, opt-in comparison groups, flexible option attributes, display order, variant-specific image and recoverable image visibility.
- Pack cards update exact price, MRP, discount, savings, unit price, SKU and verified image. Server-side calculations distinguish MRP savings from comparable-pack savings. Best value is the lowest comparable available unit rate, not automatically the largest size.
- Cards, catalog price filtering and sorting share the purchasable pack price. Multiple sizes lead to Choose size; disabled packs cannot fall back to base-product purchase. Variant cart lines and order snapshots remain exact.
- CRM supports add/edit/disable/order packs, exact-photo assignment, audited stock adjustment links and recoverable photo removal/restore. Uploads produce optimized thumbnails. Importer supports explicit Variant Image URLs and structured option attributes without assuming units.
- Nine viewport widths exercised with disposable multi-pack browser fixtures. Screenshots reviewed at 320 and 1440; real live/local product comparison at 390 informed reduced image/title spacing. Not a claim of full Shopify pixel parity.
- Remaining data: 4,342 missing original product images, unassigned pack-specific photos, verified product-family mappings/quantities and two existing duplicate-SKU groups requiring reconciliation. No existing SKUs were renamed.
- Full audit, commands, changed files and staff workflow: `docs/variant-buying-experience.md`.
- Final verification: all 133 tests pass with browser suites enabled; Django system checks and migration-drift checks pass. Backup comparison confirms unchanged existing product/variant prices, names, SKUs and stock, and unchanged historical order snapshots.

| Page/component | Reference | Django URL | Desktop | Mobile | Functional | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Variant buying panel | Requested SuryaVets-themed improvement | /product/{slug}/ | Screenshot reviewed | Nine widths tested | Price, image, stock, quantities and Buy now | IMPLEMENTED; REAL PACK DATA REQUIRED |
| Product cards | SuryaVets reusable cards | /categories/ | Tested | Grid overflow checked | From price and Choose size | IMPLEMENTED |
| Pack management | Original CRM | /crm/inventory/{id}/packs/new/ | Form tested | Responsive | Add/edit/disable/order/image; audited stock | IMPLEMENTED |
| Photo management | Original CRM | /crm/inventory/{id}/images/{id}/ | Form tested | Responsive | Main photo/order/remove/restore | IMPLEMENTED |

## P. Existing source pack families and requested stock balance

- Linked 221 families containing 498 original product records; 277 siblings are represented under shared catalog cards. Original URLs, variant ownership, prices, SKUs, orders and inventory history are preserved. This supersedes section O's earlier zero real multi-pack page status; it does not destructively merge records.
- Set all 6,677 variants and 20 simple products to stock 10, with 6,692 new inventory adjustments. This is an owner-requested balance, not verified physical inventory. Visibility/tracking flags were not changed. Future purchases reduce stock normally.
- Held 287 unclear families for review; no manufacturer-only sizes or selling prices invented. Missing photos and source label accuracy remain separate review items.
- Full suite: 139 tests passed, including linked-source pack selection/cart/order journeys across nine widths. Django checks and migration-drift checks pass. Backup comparison confirms unchanged historical product/variant identity and prices, order items and prior inventory movements.
- Guide, exact commands, local reports and rollback checkpoint: `docs/pack-family-stock-update.md`.

| Page/component | Reference | Django URL | Desktop | Mobile | Functional | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Existing multi-pack families | Supplied Shopify records; live N&D 7KG label/price checked | /product/n-d-gf-chic-adu-mini-dry-food-800gm/ | Actual page reviewed | Linked-source fixtures tested | Exact source pack pricing/cart/orders | 221 LINKED; 287 REQUIRE REVIEW |
| Stock reset | Explicit owner request | CRM stock pages | Backend verified | Backend verified | Audited, retry-safe, 10 per pack/simple product | APPLIED LOCALLY |

## Q. Customer account and shared CRM order tracking

- Initial thirteen-point architecture audit: `docs/account-order-audit.md`. Continued the existing Desktop/suryavets-django project; the alternatively named Desktop/suryavets directory does not exist.
- Reused Django User/email authentication, Order/OrderItem snapshots, addresses, cart, CRM permissions and cancellation ledger. Added migrations 0012–0013 for structured shared events, shipment details, separate return state, expanded payment/fulfillment states, profile phone, owned pets/wishlist/support and a deduplicated notification outbox.
- Customer and CRM pages read the same order and event rows. Valid staff updates become visible on customer page reload; internal notes remain staff-only. Status transitions are guarded, shipped orders require courier/AWB and payment is independent from delivery. Return approval/refund recording is not an actual refund or automatic restock.
- Customer dashboard, paginated order history, vertical tracker, exact-pack/current-price Buy again, pets, wishlist, address CRUD/default/checkout selection, profile, password change and order-linked support implemented. CRM adds attention counts, date/status/payment/returns filters, structured timeline and customer support replies.
- Full regression suite: 156 tests passed with browser suites enabled. Expanded account suite: 20 focused tests passed, including four additional cases. Account overflow verified at nine widths from 320 to 1440; shared CRM-to-customer event visibility and exact-pack reorder tested in disposable browser fixtures. Mobile tracker and desktop dashboard screenshots reviewed.
- Read-only backup comparison confirms all pre-existing order, item, product, variant, inventory movement, address and User rows unchanged. Only known historical creation time was backfilled; no fake milestone times or legacy notifications.
- Remaining boundaries: actual email transport/worker deployment, verified self-service email change, password recovery, Google OAuth, real payment/refund integration, private pet photos, return/refund business policy and audited exceptional corrections. No Shopify/DNS/Render changes.
- Staff workflow, changed files, migration commands and safety details: `docs/account-order-management.md`.
- Final post-polish rerun: 21 account unit/browser tests passed; system checks and migration drift remain clean.

| Page/component | Reference | Django URL | Desktop | Mobile | Functional | Status |
| --- | --- | --- | --- | --- | --- | --- |
| My account | Requested original SuryaVets-themed design | /account/ | Reviewed | Nine widths | Dashboard and owned account data | IMPLEMENTED LOCALLY |
| Customer order tracker | Shared Order/OrderStatusHistory | /account/orders/ | Tested | Vertical tracker reviewed | Status/history, exact variants, current-price reorder | IMPLEMENTED LOCALLY |
| CRM orders | Existing CRM extended | /crm/orders/ | Tested | Seven widths | Guarded transitions, shipment, reviews, timeline | IMPLEMENTED LOCALLY |
| Support | Simple structured requests | /account/support/ and /crm/support/ | Tested | Overflow tested | Owned order links and customer-visible replies | IMPLEMENTED LOCALLY |
| Notifications | Shared event outbox | send_order_notifications command | Backend tested | — | Deduplicated, disabled by default | TRANSPORT/DEPLOYMENT REMAINS |

## Purchase flow update — 13 September 2026

Full audit, changed-file inventory, configuration, recovery procedures and caveats: `docs/purchase-flow-20260913.md`.

- Normal Add to Cart now opens `/cart/`; explicit Buy Now opens checkout. Existing variant/cart/price checks are reused.
- Additive migration 0014 introduces test-gateway attempts, Awaiting-payment status and customer/admin outbox audiences. Database backup and old-column comparisons confirm existing data is unchanged.
- Test-only Razorpay adapter checks HMAC and captured payment/order data server-side; signed webhooks and callbacks share an idempotent finalizer. No online confirmation is sent for unverified payments. Uncertain creation requires reconciliation, not another payment attempt.
- Customer/admin HTML and plain-text messages use the existing event outbox and after-commit delivery. SMTP errors cannot undo orders; ambiguous delivery is retained for provider review, never automatically resent.
- Mobile confirmation pages and both email templates have been visually inspected. COD, exact variants, shared CRM/account orders and simulated online checkout are exercised in disposable browser fixtures.
- Real Razorpay test keys and SMTP credentials are not configured. No real payment or inbox-delivery test was performed. Both integrations remain disabled locally. Unpaid reservation expiry and live payment/refund operations remain production prerequisites.
- No Shopify, DNS, deployment or PIN-code-system changes.
