////////////////////////////////////////////////////////////////////////////////
//
// Filename: 	llsdspi.v
//
// Project:	SD-Card controller, using a shared SPI interface
//
// Purpose:	This file implements the "lower-level" interface to the
//		SD-Card controller.  Specifically, it turns byte-level
//	interaction requests into SPI bit-wise interactions.  Further, it
//	handles the request and grant for the SPI wires (i.e., it requests
//	the SPI port by pulling o_cs_n low, and then waits for i_bus_grant
//	to be true before continuing.).  Finally, the speed/clock rate of the
//	communication is adjustable as a division of the current clock rate.
//
//	i_speed
//		This is the number of clocks (minus one) between SPI clock
//		transitions.  Hence a '0' (not tested, doesn't work) would
//		result in a SPI clock that alternated on every input clock
//		equivalently dividing the input clock by two, whereas a '1'
//		would divide the input clock by four.
//
//		In general, the SPI clock frequency will be given by the
//		master clock frequency divided by twice this number plus one.
//		In other words,
//
//		SPIFREQ=(i_clk FREQ) / (2*(i_speed+1))
//
//	i_stb
//		True if the master controller is requesting to send a byte.
//		This will be ignored unless o_idle is false.
//
//	i_byte
//		The byte that the master controller wishes to send across the
//		interface.
//
//	(The external SPI interface)
//
//	o_stb
//		Only true for one clock--when a byte is valid coming in from the
//		interface, this will be true for one clock (a strobe) indicating
//		that a valid byte is ready to be read.
//
//	o_byte
//		The value of the byte coming in.
//
//	o_idle
//		True if this low-level device handler is ready to accept a
//		byte from the incoming interface, false otherwise.
//
//	i_bus_grant
//		True if the SPI bus has been granted to this interface, false
//		otherwise.  This has been placed here so that the interface of
//		the XuLA2 board may be shared between SPI-Flash and the SPI
//		based SDCard.  An external arbiter will determine which of the
//		two gets to control the clock and mosi outputs given their
//		cs_n requests.  If control is not granted, i_bus_grant will
//		remain low as will the actual cs_n going out of the FPGA.
//
//
//
// Creator:	Dan Gisselquist, Ph.D.
//		Gisselquist Technology, LLC
//
////////////////////////////////////////////////////////////////////////////////
//
// Copyright (C) 2016, Gisselquist Technology, LLC
//
// This program is free software (firmware): you can redistribute it and/or
// modify it under the terms of  the GNU General Public License as published
// by the Free Software Foundation, either version 3 of the License, or (at
// your option) any later version.
//
// This program is distributed in the hope that it will be useful, but WITHOUT
// ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY or
// FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
// for more details.
//
// You should have received a copy of the GNU General Public License along
// with this program.  (It's in the $(ROOT)/doc directory, run make with no
// target there if the PDF file isn't present.)  If not, see
// <http://www.gnu.org/licenses/> for a copy.
//
// License:	GPL, v3, as defined and found on www.gnu.org,
//		http://www.gnu.org/licenses/gpl.html
//
//
////////////////////////////////////////////////////////////////////////////////
//
//
`default_nettype	none
//
module	llsdspi(i_clk, i_speed, i_cs, i_stb, i_byte,
		o_cs_n, o_sclk, o_mosi, i_miso,
		o_stb, o_byte, o_idle, i_bus_grant);
	parameter	SPDBITS = 7,
		STARTUP_CLOCKS = 75;
	parameter [0:0]	OPT_SPI_ARBITRATION = 1'b0;
	//
	input	wire		i_clk;
	// Parameters/setup
	input	wire	[(SPDBITS-1):0]	i_speed;
	// The incoming interface
	input	wire		i_cs;
	input	wire		i_stb;
	input	wire	[7:0]	i_byte;
	// The actual SPI interface
	output	reg		o_cs_n, o_sclk, o_mosi;
	input	wire		i_miso;
	// The outgoing interface
	output	reg		o_stb;
	output	reg	[7:0]	o_byte;
	output	wire		o_idle;
	// And whether or not we actually own the interface (yet)
	input	wire		i_bus_grant;

	localparam [3:0]	LLSDSPI_IDLE    = 4'h0,
				LLSDSPI_HOTIDLE	= 4'h1,
				LLSDSPI_WAIT	= 4'h2,
				LLSDSPI_START	= 4'h3;
//
	reg			r_z_counter;
	reg	[(SPDBITS-1):0]	r_clk_counter;
	reg			r_idle;
	reg		[3:0]	r_state;
	reg		[7:0]	r_byte, r_ireg;
	wire			byte_accepted;

	reg	startup_hold;
	generate if (STARTUP_CLOCKS > 0)
	begin : WAIT_FOR_STARTUP
		localparam	STARTUP_BITS = $clog2(STARTUP_CLOCKS);
		reg	[STARTUP_BITS-1:0]	startup_counter;
		reg				past_sclk;

		initial	past_sclk = 1;
		always @(posedge i_clk)
			past_sclk <= o_sclk;

		initial startup_counter = STARTUP_CLOCKS[STARTUP_BITS-1:0];
		initial	startup_hold = 1;
		always @(posedge i_clk)
		if (startup_hold && !past_sclk && o_sclk)
		begin
			if (|startup_counter)
				startup_counter <= startup_counter - 1;
			startup_hold <= (startup_counter > 0);
		end
	end else begin

		always @(*)
			startup_hold = 0;

	end endgenerate

	assign	byte_accepted = (i_stb)&&(o_idle);

	////////////////////////////////////////////////////////////////////////
	//
	// Clock divider and speed control
	//
	initial	r_clk_counter = 7'h0;
	initial	r_z_counter = 1'b1;
	always @(posedge i_clk)
	begin
		if (!startup_hold && (!i_cs || (OPT_SPI_ARBITRATION && !i_bus_grant)))
		begin
			// Hold, waiting for some action
			r_clk_counter <= 0;
			r_z_counter <= 1'b1;
        end else if ((startup_hold || byte_accepted))
		begin
			r_clk_counter <= i_speed;
			r_z_counter <= (i_speed == 0);
		end else if (!r_z_counter)
		begin
			r_clk_counter <= (r_clk_counter - 1);
			r_z_counter <= (r_clk_counter == 1);
		end else if ((r_state > LLSDSPI_WAIT)&&(!r_idle))
		begin
			if (r_state >= LLSDSPI_START+8)
			begin
				r_clk_counter <= 0;
				r_z_counter <= 1;
			end else begin
				r_clk_counter <= i_speed;
				r_z_counter <= (i_speed == 0);
			end
		end
	end


	////////////////////////////////////////////////////////////////////////
	//
	// Control o_stb, o_cs_n, and o_mosi
	//
	initial	o_stb  = 1'b0;
	initial	o_cs_n = 1'b1;
	initial	o_sclk = 1'b1;
	initial	r_state = LLSDSPI_IDLE;
	initial	r_idle  = 0;
	always @(posedge i_clk)
	begin
		o_stb <= 1'b0;
		o_cs_n <= (startup_hold || !i_cs);
		if (!i_cs)
		begin
			// No request for action.  If anything, a request
			// to close up/seal up the bus for the next transaction
			// Expect to lose arbitration here.
			r_state <= LLSDSPI_IDLE;
			r_idle <= (r_z_counter);
			o_sclk <= 1'b1;
		end else if (!r_z_counter)
			r_idle <= 1'b0;
		else if (r_state == LLSDSPI_IDLE)
		begin
			o_sclk <= 1'b1;
			r_idle <= (!startup_hold);
			if (byte_accepted)
			begin
				r_byte <= i_byte[7:0];
				if (OPT_SPI_ARBITRATION)
					r_state <= (!o_cs_n && i_bus_grant)
						? LLSDSPI_START:LLSDSPI_WAIT;
				else
					r_state <= LLSDSPI_START;
				r_idle <= 1'b0;
				o_mosi <= i_byte[7];
			end
		end else if (r_state == LLSDSPI_WAIT)
		begin
			r_idle <= 1'b0;
			o_sclk <= 1'b1;
			if (!OPT_SPI_ARBITRATION || i_bus_grant)
				r_state <= LLSDSPI_START;
		end else if (r_state == LLSDSPI_HOTIDLE)
		begin
			// The clock is low, the bus is granted, we're just
			// waiting for the next byte to transmit
			o_sclk <= 1'b1;
			if (byte_accepted)
			begin
				r_byte <= { i_byte[6:0], 1'b1 };
				r_state <= LLSDSPI_START+1;
				r_idle <= 1'b0;
				o_mosi <= i_byte[7];
				o_sclk <= 1'b0;
			end else
				r_idle <= 1'b1;
		end else if (o_sclk)
		begin
			o_mosi <= r_byte[7];
			r_byte <= { r_byte[6:0], 1'b1 };
			r_state <= r_state + 1;
			o_sclk <= 1'b0;
			if (r_state >= LLSDSPI_START+8)
			begin
				r_state <= LLSDSPI_HOTIDLE;
				r_idle <= 1'b1;
				o_stb <= 1'b1;
				o_byte <= r_ireg;
				o_sclk <= 1'b1;
			end else
				r_state <= r_state + 1;
		end else begin
			r_ireg <= { r_ireg[6:0], i_miso };
			o_sclk <= 1'b1;
		end

		if (startup_hold)
		begin
			r_idle <= 0;
			o_cs_n <= 1;
			if (r_z_counter)
				o_sclk <= !o_sclk;
		end
	end

	assign o_idle = (r_idle)&&( (i_cs)&&(!OPT_SPI_ARBITRATION || i_bus_grant) );
endmodule


