import { themeInitScript } from "@/lib/theme";

/**
 * Blocking-before-paint theme bootstrap for the App Router.
 * Place in the root layout `<head>` to prevent a flash of the wrong theme.
 */
export function ThemeScript() {
  return (
    <script
      id="padeya-theme-script"
      dangerouslySetInnerHTML={{ __html: themeInitScript }}
    />
  );
}
