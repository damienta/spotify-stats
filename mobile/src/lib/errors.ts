/** An API answer that wasn't OK, with its HTTP status. */
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
  }
}
