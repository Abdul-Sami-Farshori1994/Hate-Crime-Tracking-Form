import { Link } from 'react-router-dom'
import { formLoginPath } from '../paths'
import { AppShell, HeroCard, Pill, SurfaceCard } from '../components/forms-ui'

export default function ThankYouPage() {
  return (
    <AppShell width="form">
      <div className="mx-auto max-w-3xl space-y-6">
        <HeroCard
          centered
          showLogo
          logoSize="md"
          eyebrow="Submission Complete"
          title="Thank you for sharing your response"
          description="Your report has been submitted successfully. You can return to the shared sign-in page if another response needs to be entered."
        >
          <div className="flex flex-wrap gap-2">
            <Pill tone="success">Saved successfully</Pill>
            <Pill>Ready for review</Pill>
          </div>
        </HeroCard>

        <SurfaceCard className="text-center">
          <p className="text-sm leading-6 text-slate-600">
            The response is now available to administrators in the dashboard for review and analytics.
          </p>
          <Link
            className="mt-5 inline-flex items-center justify-center rounded-2xl bg-violet-600 px-5 py-3 text-sm font-medium text-white shadow-sm transition hover:bg-violet-700"
            to={formLoginPath()}
          >
            Back to sign-in
          </Link>
        </SurfaceCard>
      </div>
    </AppShell>
  )
}
