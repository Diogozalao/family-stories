import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";

import "./i18n";
import "./store/theme";
import "./index.css";
import App from "./App";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      refetchOnWindowFocus: false,
      staleTime: 10_000,
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <App />
        <Toaster
          position="bottom-right"
          toastOptions={{
            className:
              "!bg-white dark:!bg-stone-900 !text-stone-900 dark:!text-stone-100 " +
              "!border !border-stone-200 dark:!border-stone-800 !shadow-lift !rounded-xl",
          }}
        />
      </QueryClientProvider>
    </BrowserRouter>
  </StrictMode>,
);
