type AnalyticsProperties = Record<string, string | number | boolean | null | undefined>;

let initialized = false;

export async function trackEvent(name: string, properties: AnalyticsProperties = {}) {
  const apiKey = process.env.NEXT_PUBLIC_AMPLITUDE_API_KEY;
  if (!apiKey || typeof window === "undefined") {
    return;
  }

  const amplitude = await import("@amplitude/analytics-browser");
  if (!initialized) {
    amplitude.init(apiKey, undefined, {
      defaultTracking: {
        sessions: true,
        pageViews: true,
        formInteractions: false,
        fileDownloads: false,
      },
    });
    initialized = true;
  }

  amplitude.track(name, sanitize(properties));
}

function sanitize(properties: AnalyticsProperties): AnalyticsProperties {
  return Object.fromEntries(
    Object.entries(properties).filter(([key]) => !/resume|token|secret|password/i.test(key)),
  );
}

