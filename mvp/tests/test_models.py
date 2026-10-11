from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    Category,
    DocType,
    DocumentTemplate,
    Offer,
    OfferDocument,
    Segment,
    Technology,
)


def make_session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_offer_roundtrip() -> None:
    db = make_session()
    segment = Segment(code="W3_FIX_CB_CNS", name="Fisso CB Consumer")
    tech = Technology(code="FWA", name="FWA Indoor", max_download_mbps=300, max_upload_mbps=50)
    template = DocumentTemplate(code="SINTESI_FISSE", doc_type=DocType.SINTESI,
                                category=Category.FISSE, version=1, file_path="x.docx")
    db.add_all([segment, tech, template])
    db.flush()

    offer = Offer(
        name="SUPER Internet Casa 5G",
        name_key="super internet casa 5g",
        category=Category.FISSE,
        segment_id=segment.id,
        technology_id=tech.id,
    )
    db.add(offer)
    db.flush()
    doc = OfferDocument(offer_id=offer.id, doc_type=DocType.SINTESI, template_id=template.id)
    db.add(doc)
    db.commit()

    assert offer.id is not None
    assert doc.offer_id == offer.id
