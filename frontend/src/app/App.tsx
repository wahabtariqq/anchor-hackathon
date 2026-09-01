import { ThemeProvider } from "next-themes";
import { RouterProvider } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { router } from "./router";

// Dark-only app (index.html pins class="dark" so there's no flash before this mounts).
// forcedTheme keeps next-themes' own consumers — just Toaster today — in agreement,
// with no toggle to build since there's only ever one theme.
export function App() {
  return (
    <ThemeProvider attribute="class" defaultTheme="dark" forcedTheme="dark">
      <RouterProvider router={router} />
      <Toaster />
    </ThemeProvider>
  );
}
