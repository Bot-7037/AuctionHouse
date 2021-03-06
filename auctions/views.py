from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from django.contrib.auth.decorators import login_required
from datetime import datetime, timezone
from django.urls import reverse

from .models import Auction, Bid
from .forms import ImageUploadForm

# Main page
def index(request):
    # First get all auctions and resolve them
    auction_list = Auction.objects.all()
    for a in auction_list:
        a.resolve()
    # Get all active auctions, oldest first
    latest_auction_list = auction_list.filter(is_active=True).order_by('date_added')
    template = loader.get_template('auctions/index.html')
    context = {
        'title': "Active auctions",
        'auction_list': latest_auction_list,
    }
    return HttpResponse(template.render(context, request))

def auctions(request):
    # Get all auctions, newest first
    auction_list = Auction.objects.order_by('-date_added')
    for a in auction_list:
        a.resolve()
    template = loader.get_template('auctions/index.html')
    context = {
        'title': "All auctions",
        'auction_list': auction_list,
    }
    return HttpResponse(template.render(context, request))

# Details on some auction
def detail(request, auction_id):
    auction = get_object_or_404(Auction, pk=auction_id)
    auction.resolve()
    already_bid = False
    if request.user.is_authenticated:
        if auction.author == request.user:
            own_auction = True
            return render(request, 'auctions/detail.html', {'auction': auction, 'own_auction': own_auction})

        user_bid = Bid.objects.filter(bidder=request.user).filter(auction=auction).first()
        if user_bid:
            already_bid = True
            bid_amount = user_bid.amount
            return render(request, 'auctions/detail.html', {'auction': auction, 'already_bid': already_bid, 'bid_amount': bid_amount})

    return render(request, 'auctions/detail.html', {'auction': auction, 'already_bid': already_bid})

@login_required
def bid(request, auction_id):
    auction = get_object_or_404(Auction, pk=auction_id)
    auction.resolve()
    bid = Bid.objects.filter(bidder=request.user).filter(auction=auction).first()

    if not auction.is_active:
        return render(request, 'auctions/detail.html', {
            'auction': auction,
            'error_message': "The auction has expired.",
        })

    try:
        bid_amount = request.POST['amount']
        if not bid_amount or int(bid_amount) < auction.min_value:
            raise(KeyError)

        if not bid: # if bid object does not exist
            bid = Bid()
            bid.auction = auction
            bid.bidder = request.user
        bid.amount = bid_amount
        bid.date = datetime.now(timezone.utc)
    except (KeyError):
        # Redisplay the auction details.
        return render(request, 'auctions/detail.html', {
            'auction': auction,
            'error_message': "Invalid bid amount.",
        })
    else:
        bid.save()
        return HttpResponseRedirect(reverse('my_bids', args=()))

# Create auction
@login_required
def create(request):
    submit_button = request.POST.get('submit_button')
    if submit_button:
        try:
            title = request.POST['title']
            min_value = request.POST['min_value']
            if not title or not min_value:
                raise(KeyError)
        except (KeyError):
            return render(request, 'auctions/create.html', {
                'error_message': "Please fill the required fields.",
            })
        else:
            auction = Auction()
            auction.author = request.user
            auction.title = title
            auction.min_value = min_value
            auction.desc = request.POST['description']
            form = ImageUploadForm(request.POST, request.FILES)
            if form.is_valid():
                image = form.cleaned_data['image']
                auction.image = image
            auction.date_added = datetime.now(timezone.utc)
            auction.save()
            return HttpResponseRedirect(reverse('my_auctions', args=()))
    else:
        return render(request, 'auctions/create.html')


@login_required
def my_auctions(request):
    my_auctions_list = Auction.objects.all().filter(author=request.user).order_by('-date_added')
    for a in my_auctions_list:
        a.resolve()
    template = loader.get_template('auctions/my_auctions.html')
    context = {
        'my_auctions_list': my_auctions_list,
    }
    return HttpResponse(template.render(context, request))

@login_required
def my_bids(request):
    my_bids_list = Bid.objects.all().filter(bidder=request.user).order_by('-date')
    for b in my_bids_list:
        b.auction.resolve()

    template = loader.get_template('auctions/my_bids.html')
    context = {
        'my_bids_list': my_bids_list,
    }
    return HttpResponse(template.render(context, request))
