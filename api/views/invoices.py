from fastapi import APIRouter, Depends, HTTPException, Response, Security
from fastapi.responses import StreamingResponse

from api import crud, models, pagination, schemes, utils
from api.ext import export as export_ext
from api.invoices import InvoiceStatus

router = APIRouter()


async def get_invoice_noauth(model_id: str):
    item = await utils.database.get_object(models.Invoice, model_id)
    return item


@router.get("/order_id/{order_id}", response_model=schemes.DisplayInvoice)
async def get_invoice_by_order_id(order_id: str):
    item = await utils.database.get_object(
        models.Invoice, order_id, custom_query=models.Invoice.query.where(models.Invoice.order_id == order_id)
    )
    return item


@router.get("/export")
async def export_invoices(
    response: Response,
    pagination: pagination.Pagination = Depends(),
    export_format: str = "json",
    add_payments: bool = False,
    all_users: bool = False,
    user: models.User = Security(utils.authorization.AuthDependency(), scopes=["invoice_management"]),
):
    if all_users and not user.is_superuser:
        raise HTTPException(403, "Not enough permissions")
    # always full list for export
    pagination.limit = -1
    pagination.offset = 0
    query = pagination.get_base_query(models.Invoice).where(models.Invoice.status == InvoiceStatus.COMPLETE)
    if not all_users:
        query = query.where(models.Invoice.user_id == user.id)
    data = await pagination.get_list(query)
    await utils.database.postprocess_func(data)
    data = list(export_ext.db_to_json(data, add_payments))
    now = utils.time.now()
    filename = now.strftime(f"bitcartcc-export-%Y%m%d-%H%M%S.{export_format}")
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    response.headers.update(headers)
    if export_format == "json":
        return data
    else:
        return StreamingResponse(
            iter([export_ext.json_to_csv(data).getvalue()]),
            media_type="application/csv",
            headers=headers,
        )


@router.patch("/{model_id}/customer", response_model=schemes.DisplayInvoice)
async def update_invoice(
    model_id: str,
    data: schemes.CustomerUpdateData,
):
    item = await utils.database.get_object(models.Invoice, model_id)
    kwargs = {}
    for field, value in data:
        if not getattr(item, field) and value:
            kwargs[field] = value
    if kwargs:
        await utils.database.modify_object(item, kwargs)
    return item


utils.routing.ModelView.register(
    router,
    "/",
    models.Invoice,
    schemes.Invoice,
    schemes.CreateInvoice,
    schemes.DisplayInvoice,
    custom_methods={
        "post": crud.invoices.create_invoice,
        "batch_action": crud.invoices.batch_invoice_action,
    },
    request_handlers={"get_one": get_invoice_noauth},
    post_auth=False,
    scopes=["invoice_management"],
    custom_commands={"mark_complete": crud.invoices.mark_invoice_complete, "mark_invalid": crud.invoices.mark_invoice_invalid},
)
