// Basic E2E test
describe('GestVenv Web UI', () => {
  it('visits the app root url', () => {
    cy.visit('/')
    cy.contains('h1', 'GestVenv')
  })

  it('navigates to environments page', () => {
    cy.visit('/')
    cy.get('nav').contains('Environnements').click()
    cy.url().should('include', '/environments')
  })
})