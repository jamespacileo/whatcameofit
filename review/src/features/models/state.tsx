import { type ModelState } from '@/lib/api'
import { Badge } from '@/components/ui/badge'

const number = new Intl.NumberFormat('en-GB')

// One model's state in one environment, worded the same everywhere it is shown.
export function StateCell({ state }: { state?: ModelState }) {
  if (!state || state.status === 'unavailable')
    return <Badge variant='outline'>not readable yet</Badge>
  if (state.status === 'absent')
    return (
      <span title={state.reason}>
        <Badge variant='secondary'>absent</Badge>
      </span>
    )
  return (
    <span className='tabular-nums'>
      {number.format(state.inCurrent ?? state.rows)}
      {state.inCurrent != null && state.inCurrent !== state.rows && (
        <span className='text-muted-foreground'>
          {' '}
          of {number.format(state.rows)}
        </span>
      )}
    </span>
  )
}

export { number }
