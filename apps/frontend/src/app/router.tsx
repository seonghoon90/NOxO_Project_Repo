import { createBrowserRouter } from 'react-router-dom'
import { App } from './App'
import { AboutPage } from '../pages/AboutPage'
import { DatabasePage } from '../pages/DatabasePage'
import { DigitalTwinPage } from '../pages/DigitalTwinPage'
import { ServicePage } from '../pages/ServicePage'
import { TeamPage } from '../pages/TeamPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <ServicePage /> },
      { path: 'about', element: <AboutPage /> },
      { path: 'database', element: <DatabasePage /> },
      { path: 'db', element: <DatabasePage /> },
      { path: 'digital-twin', element: <DigitalTwinPage /> },
      { path: 'dt', element: <DigitalTwinPage /> },
      { path: 'team', element: <TeamPage /> },
    ],
  },
])
