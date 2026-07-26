/** Auth glass card fields — fixed contrast; ignores light-theme input tokens. */
export const authFieldOnDarkControlClass =
  "auth-field-on-dark !border-white/20 !bg-[#141414] !text-white shadow-none placeholder:!text-white/45 hover:!border-white/30 focus:!border-[#8EF012] focus:!ring-0 focus:!ring-offset-0 focus:!shadow-[0_0_0_2px_rgb(142_240_18_/_0.35)] focus:!ring-offset-transparent read-only:!bg-[#141414] read-only:!text-white disabled:!bg-[#141414] disabled:!text-white/55 [color-scheme:dark] transition-[border-color,box-shadow] duration-150";

export const authFieldOnDarkLabelClass =
  "text-xs font-bold uppercase tracking-[0.08em] !text-white/90";

export const authFieldOnDarkHintClass = "text-xs !text-white/55";

/** Native selects on dark auth cards (location cascade, etc.). */
export const authFieldOnDarkSelectClass =
  "auth-field-on-dark h-11 w-full rounded-[var(--radius-md)] !border-white/20 !bg-[#141414] px-3 text-sm font-semibold !text-white !shadow-none hover:!border-white/30 focus:!border-[#8EF012] focus:outline-none focus:!ring-2 focus:!ring-[#8EF012]/35 disabled:opacity-45 [color-scheme:dark]";