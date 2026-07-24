/** Shared marketplace card / rail sizing for consistent section height. */

/** Image area — square tiles match Shop all grid density. */
export const MARKETPLACE_CARD_IMAGE =
  "relative block w-full shrink-0 overflow-hidden aspect-square";

/** Responsive product grid (Featured, Event, Drops, Vault, Shop all). */
export const MARKETPLACE_PRODUCT_GRID =
  "grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4";

/** HomeCardCarousel desktop columns (mobile = horizontal snap). */
export const MARKETPLACE_CAROUSEL_GRID =
  "sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4";

export const MARKETPLACE_CAROUSEL_SLIDE = "w-[min(82vw,17.5rem)]";

export const MARKETPLACE_HOST_SHOP_CAROUSEL_GRID =
  "sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4";

/** Horizontal rail item width (legacy rails). */
export const MARKETPLACE_RAIL_ITEM =
  "snap-start shrink-0 min-w-[15.5rem] sm:min-w-[14.75rem] md:min-w-0";

/** Card body padding for product-style cards. */
export const MARKETPLACE_CARD_BODY =
  "flex flex-1 flex-col gap-1.5 p-3 sm:p-4";

export const MARKETPLACE_CARD_TITLE =
  "line-clamp-2 text-base font-extrabold leading-snug tracking-tight text-paper";

export const MARKETPLACE_CARD_PRICE = "text-lg font-extrabold tracking-tight text-primary";
